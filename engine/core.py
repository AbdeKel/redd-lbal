"""
Redd Lbal inference engine - pure Python standard library (runs anywhere, incl. LinuxONE / s390x).

    from engine.core import Engine
    eng = Engine("model/redd_lbal.json")
    r = eng.analyze("Votre colis est bloqué, payez 12 DH : barid-ma.top", sender="+44 7700 900123")
    r["verdict"], r["risk"], eng.explain(r, "dar")

Brain 1 (ML) + Brain 2 (rules) -> one risk score, a verdict, a scam type and the evidence.
Mirrors webapp/engine.js exactly (see tests/parity_test.py).
"""
import json
import math
import re
import time

from .ml import MLModel
from .text import normalize_token, tokenize

AR_RE = re.compile(r"[؀-ۿ]")
IP_RE = re.compile(r"^[0-9]{1,3}(\.[0-9]{1,3}){3}$")
SCHEME_RE = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.-]*)://")
TWO_DIGIT_CC = {"20", "27", "30", "31", "32", "33", "34", "36", "39", "40", "41", "43", "44", "45", "46", "47", "48",
                "49", "51", "52", "53", "54", "55", "56", "57", "58", "60", "61", "62", "63", "64", "65", "66", "81",
                "82", "84", "86", "90", "91", "92", "93", "94", "95", "98"}
HOMO = str.maketrans({"0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "7": "t", "-": ""})


def sigmoid(z):
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z))))


def osa_distance(a, b, maxd=3):
    """Optimal string alignment (Damerau-Levenshtein) distance with early exit."""
    if abs(len(a) - len(b)) > maxd:
        return maxd + 1
    prev2, prev = None, list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        cur = [i] + [0] * len(b)
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            if prev2 is not None and i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                cur[j] = min(cur[j], prev2[j - 2] + 1)
        prev2, prev = prev, cur
    return prev[len(b)]


def token_forms(t):
    """The token plus light clitic-stripped variants (Arabic و/ف/ب/ل/ك + ال, Arabizi l/f/b/w)."""
    forms = [t]
    if AR_RE.match(t):
        if t[0] in "وفبلك" and len(t) > 3:
            forms.append(t[1:])
            if t[1:3] == "ال" and len(t) > 4:
                forms.append(t[3:])
        if t.startswith("ال") and len(t) > 3:
            forms.append(t[2:])
        if t.startswith("لل") and len(t) > 3:
            forms.append(t[2:])
    elif len(t) >= 4 and t[0] in "lfbw":
        forms.append(t[1:])
    return forms


class Engine:
    def __init__(self, bundle):
        if isinstance(bundle, str):
            with open(bundle, encoding="utf-8") as fh:
                bundle = json.load(fh)
        self.b = bundle
        self.kb = bundle["knowledge"]
        self.fusion = bundle["fusion"]
        self.ml = MLModel(bundle["ml"])
        self.text = self.kb["TEXT"]
        self.rules = self.kb["RULES"]
        # compile phrase lists: concept -> list of token tuples
        self.concepts = {name: self._compile(phrases) for name, phrases in self.kb["CONCEPTS"].items()}
        for bid, br in self.kb["BRANDS"].items():
            self.concepts["brand:" + bid] = self._compile(br["names"])
        self.brands = self.kb["BRANDS"]
        self.official = []           # (domain, brand_id)
        for bid, br in self.brands.items():
            for d in br["official"]:
                self.official.append((d, bid))
        self.official_labels = {}
        for d, bid in self.official:
            lab = d.split(".")[0]
            if len(lab) >= 5:
                self.official_labels.setdefault(lab.translate(HOMO), (d, bid))

    @staticmethod
    def _compile(phrases):
        idx, wild = {}, []
        for p in phrases:
            toks = [normalize_token(w) if not w.endswith("*") else normalize_token(w[:-1]) + "*" for w in p.split()]
            toks = tuple(t for t in toks if t and t != "*")
            if not toks:
                continue
            if toks[0].endswith("*"):
                wild.append(toks)
            else:
                idx.setdefault(toks[0], []).append(toks)
        return {"idx": idx, "wild": wild}

    # ------------------------------------------------------------------ concept matching
    @staticmethod
    def _tok_ok(p, fs):
        if p.endswith("*"):
            pre = p[:-1]
            return any(f.startswith(pre) for f in fs)
        return p in fs

    def _match(self, forms, comp):
        spans = set()
        n = len(forms)
        for i in range(n):
            cands = []
            for f in forms[i]:
                cands += comp["idx"].get(f, [])
            cands += [w for w in comp["wild"] if self._tok_ok(w[0], forms[i])]
            for ph in cands:
                L = len(ph)
                if i + L > n:
                    continue
                if all(self._tok_ok(ph[k], forms[i + k]) for k in range(1, L)):
                    spans.add((i, i + L))
        return sorted(spans)

    # ------------------------------------------------------------------ links
    def _host_is(self, host, domains):
        for d in domains:
            if host == d or host.endswith("." + d):
                return d
        return None

    def analyze_link(self, raw):
        s = raw.strip()
        m = SCHEME_RE.match(s)
        scheme = m.group(1).lower() if m else ""
        rest = s[m.end():] if m else s
        host = re.split(r"[/?#]", rest, 1)[0]
        if "@" in host:
            host = host.rsplit("@", 1)[1]
        host = host.split(":")[0].lower().strip(".")
        if host.startswith("www."):
            host = host[4:]
        labels = host.split(".")
        suffix2 = ".".join(labels[-2:])
        registered = ".".join(labels[-3:]) if suffix2 in self.kb["MULTI_SUFFIXES"] and len(labels) >= 3 else suffix2
        tld = labels[-1] if labels else ""
        info = {"raw": raw, "host": host, "registered": registered, "tld": tld, "flags": [], "status": "unknown",
                "brand": None, "official": None}
        flags = info["flags"]
        if self._host_is(host, self.kb["CHAT_HOSTS"]):
            flags.append("chat")
            info["status"] = "chat"
            return info
        off = None
        for d, bid in self.official:
            if host == d or host.endswith("." + d):
                off = (d, bid)
                break
        if off is None and self._host_is(host, self.kb["OFFICIAL_SUFFIXES"]):
            off = (registered, "royaume")
        if off:
            info.update(status="official", brand=off[1], official=off[0])
            if scheme == "http":
                flags.append("http")
            return info
        if self._host_is(host, self.kb["REPUTABLE"]):
            info["status"] = "reputable"
            return info
        if IP_RE.match(host):
            flags.append("ip")
        if "xn--" in host:
            flags.append("punycode")
        if self._host_is(host, self.kb["SHORTENERS"]):
            flags.append("shortener")
        if self._host_is(host, self.kb["FREEHOST"]):
            flags.append("freehost")
        if tld in self.kb["SUS_TLDS"]:
            flags.append("susp_tld")
        if scheme == "http":
            flags.append("http")
        # official name used as a decoy inside another domain (cihbank.ma.secure-x.top)
        for d, bid in self.official + [("gov.ma", "royaume")]:
            if host.startswith(d + ".") or ("." + d + ".") in host:
                flags.append("decoy")
                info.update(brand=bid, official=d)
                break
        # brand keyword inside a non-official domain (cih-securite.com)
        if "decoy" not in flags and "shortener" not in flags and "ip" not in flags:
            parts = re.split(r"[.\-_]", host)
            for bid, br in self.brands.items():
                hit = False
                for kw in br["kw"]:
                    if (len(kw) >= 4 and kw in host) or kw in parts:
                        hit = True
                        break
                if hit:
                    flags.append("impersonation")
                    info.update(brand=bid, official=(br["official"][0] if br["official"] else ".gov.ma"))
                    break
            if "impersonation" not in flags:
                lab = registered.split(".")[0].translate(HOMO)
                if len(lab) >= 5:
                    for olab, (d, bid) in self.official_labels.items():
                        dist = osa_distance(lab, olab, 2)
                        if 0 < dist <= (1 if len(olab) < 9 else 2):
                            flags.append("typosquat")
                            info.update(brand=bid, official=d)
                            break
        info["status"] = "suspicious" if flags and flags != ["http"] else "unknown"
        return info

    # ------------------------------------------------------------------ sender
    @staticmethod
    def analyze_sender(sender):
        out = {"raw": sender or "", "kind": "none", "foreign": False, "prefix": ""}
        if not sender or not sender.strip():
            return out
        s = sender.strip()
        digits = re.sub(r"[^0-9]", "", s)
        if len(digits) >= 8 and len(re.sub(r"[0-9\s+().-]", "", s)) == 0:
            intl = s.startswith("+") or s.startswith("00")
            d = digits[2:] if s.startswith("00") else digits
            if intl and not d.startswith("212"):
                n = 1 if d[0] in "17" else (2 if d[:2] in TWO_DIGIT_CC else 3)
                out.update(kind="phone", foreign=True, prefix="+" + d[:n])
            else:
                out.update(kind="phone", prefix="+212")
        else:
            out["kind"] = "alpha"
        return out

    # ------------------------------------------------------------------ rules
    def _eval(self, cond, ctx):
        if "has" in cond:
            return bool(self._spans(cond["has"], ctx))
        if "flag" in cond:
            return bool(ctx["flags"].get(cond["flag"]))
        if "not" in cond:
            return not self._eval(cond["not"], ctx)
        if "all" in cond:
            return all(self._eval(c, ctx) for c in cond["all"])
        if "any" in cond:
            return any(self._eval(c, ctx) for c in cond["any"])
        if "near" in cond:
            a, b, w = cond["near"]
            A, B = self._spans(a, ctx), self._spans(b, ctx)
            for (s1, e1) in A:
                for (s2, e2) in B:
                    gap = s2 - e1 if e1 <= s2 else (s1 - e2 if e2 <= s1 else 0)
                    if gap <= w:
                        return True
            return False
        raise ValueError(cond)

    def _spans(self, name, ctx):
        out = []
        for n in name.split("|"):
            if n not in ctx["cache"]:
                ctx["cache"][n] = self._match(ctx["forms"], self.concepts.get(n, {"idx": {}, "wild": []}))
            out += ctx["cache"][n]
        return out

    # ------------------------------------------------------------------ main
    def analyze(self, text, sender=None):
        t0 = time.perf_counter()
        toks = tokenize(text or "")
        forms = [token_forms(t["norm"]) for t in toks]
        ctx = {"forms": forms, "cache": {}, "flags": {}}
        F = ctx["flags"]
        # links
        links = [self.analyze_link(t["raw"]) for t in toks if t["kind"] == "url"]
        nonoff = [l for l in links if l["status"] not in ("official", "reputable")]
        F["has_link"] = bool(links)
        F["link_nonofficial"] = bool(nonoff)
        F["link_unknown"] = bool(nonoff)
        F["link_official_only"] = bool(links) and all(l["status"] == "official" for l in links)
        F["link_nonofficial_foreign"] = any(not l["registered"].endswith(".ma") for l in nonoff)
        F["link_unknown_ma"] = any(l["registered"].endswith(".ma") for l in nonoff)
        for fl in ["ip", "punycode", "shortener", "chat", "freehost", "susp_tld", "http", "decoy", "impersonation", "typosquat"]:
            F["link_" + fl] = any(fl in l["flags"] for l in links)
        chat_cc = [re.sub(r"[^0-9]", "", l["raw"].split("/", 1)[-1]) for l in links if l["status"] == "chat" and "wa.me" in l["host"]]
        foreign_chat = [d for d in chat_cc if len(d) >= 8 and not d.startswith("212") and not d.startswith("0")]
        F["link_chat_foreign"] = bool(foreign_chat)
        # brands / claims mentioned in the text
        mentioned = [bid for bid in self.brands if self._spans("brand:" + bid, ctx)]
        cats = {self.brands[b]["cat"] for b in mentioned}
        F["claims_gov"] = "gov" in cats or bool(self._spans("FINE", ctx))
        F["claims_bank"] = "bank" in cats or bool(self._spans("BANK_GENERIC", ctx))
        F["claims_telco"] = "telco" in cats
        F["claims_post"] = "post" in cats
        specific = [b for b in mentioned if self.brands[b]["official"]]
        web_bad = [l for l in nonoff if l["status"] in ("suspicious", "unknown")]
        F["brand_link_mismatch"] = bool(specific and web_bad)
        # sender + phone numbers in text
        snd = self.analyze_sender(sender)
        F["sender_foreign"] = snd["foreign"]
        F["has_phone"] = any(t["kind"] == "phone" or (t["kind"] == "word" and t["raw"].isdigit() and len(t["raw"]) >= 9) for t in toks)
        F["phone_foreign"] = any(t["kind"] == "phone" and (t["raw"].strip().startswith("+") or t["raw"].strip().startswith("00"))
                                 and not re.sub(r"[^0-9]", "", t["raw"]).lstrip("0").startswith("212") for t in toks)
        # ML
        logit, contrib = self.ml.score(toks)
        p_ml = sigmoid(logit)
        # rules
        fired, best = [], {}
        for r in self.rules:
            if self._eval(r["when"], ctx):
                crit = r.get("critical", False)
                if isinstance(crit, dict):
                    crit = self._eval(crit, ctx)
                fired.append({"id": r["id"], "w": r["w"], "group": r["group"], "harm": r.get("harm", False),
                              "critical": bool(crit), "safe": r.get("safe", False), "hl": r.get("hl", []),
                              "floor": r.get("floor", 0.0)})
        for f in fired:
            g = f["group"]
            if g not in best or abs(f["w"]) > abs(best[g]):
                best[g] = f["w"]
        fz = self.fusion
        z = fz["a"] * logit + fz["b"] + sum(best.values())
        risk = sigmoid(z)
        harm = any(f["harm"] for f in fired)
        soft = set(self.kb.get("SOFT_HARM", []))
        strong = any(f["harm"] and f["id"] not in soft for f in fired)
        critical = any(f["critical"] for f in fired)
        if critical:
            risk = max(risk, fz["floor_critical"])
        elif not harm:
            risk = min(risk, fz["cap_no_harm"])
        if harm and not strong and not critical:
            risk = min(risk, fz["t_red"] - 0.01)      # ambiguous on its own -> at most "suspicious"
        safe = any(f["safe"] for f in fired)
        if not harm and not critical and not safe and p_ml >= fz.get("ml_alone", 2.0):
            risk = min(max(risk, fz.get("ml_alone_floor", 0.5)), fz["t_red"] - 0.01)   # AI alone can only say "suspicious"
        risk = max([risk] + [f["floor"] for f in fired])
        verdict = "red" if risk >= fz["t_red"] else ("amber" if risk >= fz["t_amber"] else "green")
        # parameters for explanations
        bad = next((l for l in links if l["status"] == "suspicious"), web_bad[0] if web_bad else (nonoff[0] if nonoff else None))
        offl = next((l for l in links if l["status"] == "official"), None)
        brand_for_mismatch = specific[0] if specific else None
        params = {"domain": (bad or offl or {}).get("host", ""), "tld": (bad or {}).get("tld", ""),
                  "prefix": snd["prefix"] or (("+" + foreign_chat[0][:3]) if foreign_chat else "")}
        lb = bad["brand"] if bad and bad.get("brand") else brand_for_mismatch
        if lb:
            params["brand"] = self.brands[lb]["label"]
            params["official"] = (bad.get("official") if bad and bad.get("official") else None) or \
                                 (self.brands[lb]["official"][0] if self.brands[lb]["official"] else ".gov.ma")
        if offl:
            params.setdefault("official", offl["host"])
            if not bad:
                params["domain"] = offl["host"]
        # highlights (UTF-16 offsets into the original text)
        hl = []
        for f in fired:
            if f["safe"]:
                continue
            for c in f["hl"]:
                for (s, e) in self._spans(c, ctx):
                    hl.append({"s": toks[s]["s"], "e": toks[e - 1]["e"], "kind": "rule", "rule": f["id"]})
        for t in toks:
            if t["kind"] == "url":
                li = next(l for l in links if l["raw"] == t["raw"])
                if li["status"] in ("suspicious", "unknown", "chat"):
                    hl.append({"s": t["s"], "e": t["e"], "kind": "link", "rule": "link"})
        if p_ml >= 0.5:
            ranked = sorted(range(len(toks)), key=lambda i: -contrib[i])
            for i in ranked[:4]:
                if contrib[i] > 0.12 and toks[i]["kind"] == "word":
                    hl.append({"s": toks[i]["s"], "e": toks[i]["e"], "kind": "ml", "rule": "ml", "score": round(contrib[i], 3)})
        # scam type
        stype = None
        if verdict != "green":
            scores = {}
            fired_ids = {f["id"] for f in fired}
            for typ, sig in self.kb["TYPES"].items():
                sc = 0.0
                for key, w in sig.items():
                    if key.startswith("rule:"):
                        sc += w if key[5:] in fired_ids else 0
                    elif key.startswith("flag:"):
                        sc += w if F.get(key[5:]) else 0
                    elif key.startswith("cat:"):
                        sc += w if key[4:] in cats else 0
                    elif key.startswith("brand:"):
                        sc += w if key[6:] in mentioned else 0
                    else:
                        sc += w if self._spans(key, ctx) else 0
                scores[typ] = sc
            top = max(scores, key=scores.get)
            stype = top if scores[top] >= 2 else "generic"
        signals = [{"id": f["id"], "w": f["w"], "critical": f["critical"], "safe": f["safe"], "harm": f["harm"]} for f in fired]
        signals.sort(key=lambda s: (not s["critical"], -abs(s["w"])))
        return {
            "risk": round(risk, 4), "verdict": verdict, "type": stype,
            "ml": {"prob": round(p_ml, 4), "logit": round(logit, 4)},
            "signals": signals, "params": params, "links": links, "sender": snd,
            "highlights": hl, "n_tokens": len(toks),
            "components": {"S": round(sum(best.values()), 4), "harm": harm, "strong": strong, "critical": critical, "safe": safe,
                           "floor": max([0.0] + [f["floor"] for f in fired])},
            "latency_ms": round((time.perf_counter() - t0) * 1000, 3),
        }

    # ------------------------------------------------------------------ human explanation
    def explain(self, r, lang="en"):
        T = self.text

        def tr(key, **kw):
            s = T.get(key, {}).get(lang) or T.get(key, {}).get("en", key)
            for k, v in kw.items():
                s = s.replace("{" + k + "}", str(v))
            return s

        reasons = []
        fired = {x["id"] for x in r["signals"]}
        red = self.kb.get("REDUNDANT", {})
        shown = 0
        for s in r["signals"]:
            if s["id"] in ("link_unknown",) and any(x["id"].startswith("link_") and x["id"] != "link_unknown" and not x["safe"] for x in r["signals"]):
                continue
            if any(o in fired for o in red.get(s["id"], [])):
                continue
            if not s["safe"]:
                if shown >= self.kb.get("MAX_REASONS", 99):
                    continue
                shown += 1
            reasons.append({"id": s["id"], "safe": s["safe"], "critical": s["critical"], "text": tr(s["id"], **r["params"])})
        if r["ml"]["prob"] >= 0.8 and r["verdict"] != "green":
            reasons.append({"id": "ml_high", "safe": False, "critical": False, "text": tr("ml_high")})
        if not any(s["harm"] for s in r["signals"]):
            reasons.append({"id": "no_harm", "safe": True, "critical": False, "text": tr("no_harm")})
        typ = r["type"]
        return {
            "verdict": tr("verdict_" + r["verdict"]),
            "type": tr("type_" + typ) if typ else None,
            "reasons": reasons,
            "do": tr("do_" + r["verdict"]),
            "tip": tr("tip_" + typ) if typ else None,
            "if_victim": tr("if_victim") if r["verdict"] != "green" else None,
            "share": tr("share_warning", type=tr("type_" + typ)) if r["verdict"] == "red" and typ else None,
        }
