"""
Full evaluation of Redd Lbal (+ head-to-head with the original prototype).

  python training/evaluate.py            -> reports/results.json + reports/RESULTS.md

Sets
  * test split (held out): REAL Moroccan messages (DODa, MYC YouTube, MAC tweets), UCI SMS,
    synthetic scams/legit from templates NEVER seen in training
  * challenge set (120, hand-written; rules were developed against it -> optimistic)
  * blind sets (written after freezing a version; first-run results are in reports/blind*_first_run_*.txt)
  * data/real_messages.csv  <- YOUR collected messages, automatically included when present
"""
import json
import os
import re
import statistics
import sys
import time

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from engine.core import Engine  # noqa: E402
from engine.text import tokenize  # noqa: E402

REAL_SOURCES = ["doda", "myc", "mac"]
OFFICIAL_URLS = ["https://www.cihbank.ma", "https://www.attijariwafabank.com", "https://www.bankofafrica.ma",
                 "https://www.groupebcp.com", "https://www.albaridbank.ma", "https://www.sahambank.com", "https://www.bmci.ma",
                 "https://www.iam.ma", "https://www.inwi.ma", "https://www.orange.ma", "https://www.poste.ma",
                 "https://bam-tracking.barid.ma", "https://www.cnss.ma", "https://www.asd.ma", "https://www.rsu.ma",
                 "https://amendes.justice.gov.ma", "https://infractionsroutieres.narsa.gov.ma", "https://www.tgr.gov.ma",
                 "https://www.tax.gov.ma", "https://www.daamsakane.ma", "https://www.bkam.ma", "https://www.lydec.ma",
                 "https://www.avito.ma", "https://www.jumia.ma", "https://www.oncf-voyages.ma"]


def run_engine(eng, df):
    out = []
    for t, s in zip(df["text"].astype(str), df.get("sender", pd.Series([""] * len(df))).fillna("").astype(str)):
        r = eng.analyze(t, s or None)
        out.append((r["verdict"], r["risk"], r["type"]))
    return pd.DataFrame(out, columns=["verdict", "risk", "type"], index=df.index)


class Original:
    """The friend's prototype pipeline (text NB + URL whitelist/Levenshtein/LogReg), most favourable reading:
    text model on the message, URL pipeline on the first link, final = max (as its API does)."""

    def __init__(self):
        import importlib.util
        import joblib
        spec = importlib.util.spec_from_file_location("orig_main", os.path.join(ROOT, "legacy", "main_original.py"))
        self.M = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.M)
        d = os.path.join(ROOT, "legacy", "models")
        self.tm, self.tv = joblib.load(f"{d}/text_model.joblib"), joblib.load(f"{d}/text_vectorizer.joblib")
        self.um, self.uv = joblib.load(f"{d}/url_model.joblib"), joblib.load(f"{d}/url_vectorizer.joblib")

    def url_prob(self, lien):
        M = self.M
        dom = M.extract_strict_domain(lien)
        if dom in M.WHITELIST or f"www.{dom}" in M.WHITELIST:
            return 0.0
        danger, exact, _, _ = M.check_heuristic_protection(dom)
        if exact:
            return 0.0
        if danger:
            return 1.0
        x = lien.replace("https://", "").replace("http://", "").replace("www.", "")
        return float(self.um.predict_proba(self.uv.transform([x]))[0][1])

    def prob(self, text):
        p = float(self.tm.predict_proba(self.tv.transform([text]))[0][1])
        urls = [t["raw"] for t in tokenize(text) if t["kind"] == "url"]
        if urls:
            p = max(p, self.url_prob(urls[0]))
        return p


def rates(v, y):
    v, y = pd.Series(v).values, pd.Series(y).values
    sc, lg = v[y == 1], v[y == 0]
    r = {}
    if len(sc):
        r.update(n_scam=int(len(sc)), scam_red=float((sc == "red").mean()), scam_flagged=float((sc != "green").mean()))
    if len(lg):
        r.update(n_legit=int(len(lg)), legit_red=float((lg == "red").mean()), legit_flagged=float((lg != "green").mean()))
    return r


def pct(x, n=None):
    if 0 < x < 0.001 and n:
        return f"{100 * x:.3f}% ({round(x * n)}/{n:,})"
    return f"{100 * x:.1f}%"


if __name__ == "__main__":
    eng = Engine(os.path.join(ROOT, "model", "redd_lbal.json"))
    res = {"version": eng.b["version"], "fusion": eng.fusion}
    te = pd.read_csv(os.path.join(ROOT, "data", "processed", "test.csv"))
    te = te.join(run_engine(eng, te))
    # ---- test split
    real = te[te.source.isin(REAL_SOURCES)]
    res["real_moroccan_messages"] = {**rates(real.verdict, real.label), "by_source": {s: rates(g.verdict, g.label) for s, g in real.groupby("source")}}
    uci = te[te.source == "uci"]
    res["uci_english_sms"] = rates(uci.verdict, uci.label)
    syn = te[te.source == "synthetic"]
    res["unseen_templates"] = {**rates(syn.verdict, syn.label),
                               "by_campaign": {c: rates(g.verdict, g.label) for c, g in syn.groupby("campaign")},
                               "by_lang": {l: rates(g.verdict, g.label) for l, g in syn.groupby("lang")}}
    # ---- hand-written sets
    orig = Original()
    sets = {}
    for name in ["challenge_set", "blind_set", "blind_set2", "real_messages"]:
        p = os.path.join(ROOT, "data", f"{name}.csv")
        if not os.path.exists(p):
            continue
        d = pd.read_csv(p, keep_default_na=False)
        d = d.join(run_engine(eng, d))
        d["orig_p"] = [orig.prob(t) for t in d.text]
        d["orig_verdict"] = d.orig_p.map(lambda p: "red" if p >= 0.5 else "green")
        sets[name] = {"redd_lbal": rates(d.verdict, d.label), "original": rates(d.orig_verdict, d.label),
                      "by_lang": {l: rates(g.verdict, g.label) for l, g in d.groupby("lang")},
                      "type_accuracy_on_red_scams": None}
        d.to_csv(os.path.join(ROOT, "reports", f"predictions_{name}.csv"), index=False)
    res["sets"] = sets
    # ---- original prototype on real Moroccan normal messages (sample) and on official sites
    samp = real.sample(3000, random_state=0)
    op = [orig.prob(t) for t in samp.text.astype(str)]
    res["original_on_real_messages"] = {"n": 3000, "false_alarm": float((pd.Series(op) >= 0.5).mean())}
    off_orig = [orig.url_prob(u) >= 0.5 for u in OFFICIAL_URLS]
    off_new = [eng.analyze(f"Plus d'infos : {u}")["verdict"] != "green" for u in OFFICIAL_URLS]
    res["official_moroccan_sites"] = {"n": len(OFFICIAL_URLS), "original_flagged_danger": int(sum(off_orig)),
                                      "redd_lbal_flagged": int(sum(off_new)),
                                      "original_flagged_list": [u for u, f in zip(OFFICIAL_URLS, off_orig) if f]}
    # ---- latency (pure Python, 1 core)
    texts = pd.concat([pd.read_csv(os.path.join(ROOT, "data", f"{n}.csv"), keep_default_na=False) for n in
                       ["challenge_set", "blind_set", "blind_set2"]]).text.tolist() + real.text.astype(str).sample(2000, random_state=1).tolist()
    lat = []
    for t in texts:
        t0 = time.perf_counter()
        eng.analyze(t)
        lat.append((time.perf_counter() - t0) * 1000)
    lat.sort()
    res["latency_ms"] = {"n": len(lat), "p50": round(statistics.median(lat), 3), "p95": round(lat[int(0.95 * len(lat))], 3),
                         "p99": round(lat[int(0.99 * len(lat))], 3), "mean": round(sum(lat) / len(lat), 3),
                         "msgs_per_sec_1core": int(1000 / (sum(lat) / len(lat)))}
    with open(os.path.join(ROOT, "reports", "results.json"), "w") as fh:
        json.dump(res, fh, indent=2, ensure_ascii=False)
    # ---- markdown summary
    R = res
    L = [f"# Redd Lbal v{R['version']} - evaluation", "",
         "| What | Messages | Scams caught (red) | Scams flagged (red+amber) | False alarms (red) | Flagged legit (red+amber) |",
         "|---|---|---|---|---|---|"]

    def row(label, r):
        nl = r.get("n_legit")
        return (f"| {label} | {r.get('n_scam', 0) + r.get('n_legit', 0):,} | {pct(r['scam_red']) if 'scam_red' in r else '-'} | "
                f"{pct(r['scam_flagged']) if 'scam_flagged' in r else '-'} | {pct(r['legit_red'], nl) if 'legit_red' in r else '-'} | "
                f"{pct(r['legit_flagged'], nl) if 'legit_flagged' in r else '-'} |")
    L.append(row("REAL Moroccan messages (Darija/Arabic/French, held out)", R["real_moroccan_messages"]))
    L.append(row("UCI English SMS (held out, 2012 UK marketing spam*)", R["uci_english_sms"]))
    L.append(row("Scam/legit wordings never seen in training", R["unseen_templates"]))
    for n, s in R["sets"].items():
        L.append(row(f"{n} (current engine)", s["redd_lbal"]))
    L += ["", "*UCI spam is mostly 2012 UK marketing (ringtones, dating, premium numbers). Redd Lbal targets scams: a message "
          "with no attack vector (no link, code, money or contact request) is never called a scam, so much of it is "
          "'suspicious' instead.", "",
          "**Blind sets, first run (written after freezing the engine, evaluated once, before any fix):** "
          "blind-1 on v0.2: 92.5% of 40 scams flagged, 1 false alarm in 30 legit; blind-2 on v0.3: 100% of 36 scams "
          "flagged, 0 false alarms in 25 legit (raw outputs in reports/blind*_first_run_*.txt). The 'current engine' rows "
          "above are after we learned from those misses, so they are no longer blind.", ""]
    loco_p = os.path.join(ROOT, "reports", "loco.json")
    if os.path.exists(loco_p):
        lo = json.load(open(loco_p))
        L += ["## Scam types never seen in training (leave-one-campaign-out)", "",
              "The ML brain is retrained WITHOUT any message of the campaign, then tested on it. The rules encode generic "
              "red flags (links, codes, money, pressure) written from the official guidance.", "",
              "| Held-out campaign | n | AI alone caught | Full engine flagged | Full engine red |", "|---|---|---|---|---|"]
        for c, r in lo.items():
            L.append(f"| {c} | {r['n']} | {pct(r['ml_only_caught'])} | {pct(r['engine_flagged'])} | {pct(r['engine_red'])} |")
        L.append("")
    L += ["## Original prototype vs Redd Lbal (same messages)", "",
          "| Set | Original: scams caught | Original: false alarms | Redd Lbal: scams caught (red) | Redd Lbal: false alarms (red) |", "|---|---|---|---|---|"]
    for n, s in R["sets"].items():
        o, r = s["original"], s["redd_lbal"]
        L.append(f"| {n} | {pct(o['scam_red'])} | {pct(o['legit_red'])} | {pct(r['scam_red'])} | {pct(r['legit_red'])} |")
    L += ["", f"* Original prototype on 3,000 real Moroccan messages: **{pct(R['original_on_real_messages']['false_alarm'])}** false alarms.",
          f"* Official Moroccan sites flagged as DANGER by the original: **{R['official_moroccan_sites']['original_flagged_danger']}/{R['official_moroccan_sites']['n']}** "
          f"({', '.join(R['official_moroccan_sites']['original_flagged_list'])}). Redd Lbal: {R['official_moroccan_sites']['redd_lbal_flagged']}/{R['official_moroccan_sites']['n']}.",
          f"* Latency (pure Python, 1 CPU core): p50 **{R['latency_ms']['p50']} ms**, p99 {R['latency_ms']['p99']} ms -> ~{R['latency_ms']['msgs_per_sec_1core']:,} messages/second/core.",
          "", "## Unseen templates by campaign", "", "| Campaign | n | caught (red) | flagged |", "|---|---|---|---|"]
    for c, r in sorted(R["unseen_templates"]["by_campaign"].items()):
        if "scam_red" in r:
            L.append(f"| {c} | {r['n_scam']} | {pct(r['scam_red'])} | {pct(r['scam_flagged'])} |")
    L += ["", "| Legit category | n | false alarm (red) | flagged |", "|---|---|---|---|"]
    for c, r in sorted(R["unseen_templates"]["by_campaign"].items()):
        if "legit_red" in r:
            L.append(f"| {c} | {r['n_legit']} | {pct(r['legit_red'])} | {pct(r['legit_flagged'])} |")
    with open(os.path.join(ROOT, "reports", "RESULTS.md"), "w") as fh:
        fh.write("\n".join(L) + "\n")
    print("\n".join(L))
