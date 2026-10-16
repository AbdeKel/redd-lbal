/*
 * Redd Lbal engine - JavaScript port of engine/text.py + engine/ml.py + engine/core.py.
 * Runs fully on the device (browser / Node). Same model file (model/redd_lbal.json),
 * same results as the Python engine on LinuxONE (checked by tests/parity_test.py).
 *
 *   const eng = new ReddLbal.Engine(bundle);           // bundle = parsed redd_lbal.json
 *   const r = eng.analyze(text, sender);                // verdict, risk, signals, highlights...
 *   const e = eng.explain(r, "dar" | "fr" | "ar" | "en");
 */
(function (root) {
  "use strict";
  // Character ranges are built from code points (robust to editors / file encodings).
  const R = (a, b) => String.fromCharCode(a) + "-" + String.fromCharCode(b);
  const C = (a) => String.fromCharCode(a);

  // ------------------------------------------------------------------ tokenizer
  const TLDS = "university|education|solutions|business|delivery|exchange|services|software|training|academy|careers|company|digital|express|finance|monster|network|reviews|support|systems|tickets|trading|website|africa|agency|center|credit|design|events|global|invest|london|market|moscow|online|photos|review|school|social|stream|studio|click|cloud|codes|deals|email|games|gifts|group|loans|media|money|movie|music|ninja|pages|paris|photo|press|promo|quest|space|store|today|tools|trade|video|works|world|arab|asia|bank|best|blog|bond|buzz|cash|chat|club|cyou|free|game|gift|gold|help|host|info|jobs|life|link|live|loan|mobi|name|news|page|pics|rest|sale|shop|site|tech|wiki|work|zone|app|art|bar|bet|biz|cam|cfd|com|dev|edu|fit|fun|gov|icu|inc|ink|int|llc|lol|ltd|mil|mom|net|one|org|pro|run|sbs|tel|top|uno|vip|win|xyz|ac|ad|ae|af|ag|ai|al|am|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cu|cv|cw|cx|cy|cz|de|dj|dk|dm|do|dz|ec|ee|eg|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|za|zm|zw";
  const Q = C(0xab) + C(0xbb); // « »
  const URL_SRC = "(?:https?://|www\\.)[^\\s<>\"'" + Q + "]+" +
    "|(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\\.)+(?:" + TLDS + ")(?![a-z0-9-])(?:[/?#][^\\s<>\"'" + Q + "]*)?";
  const EMAIL_SRC = "[A-Za-z0-9_.+-]+@[A-Za-z0-9-]+\\.[A-Za-z0-9.-]+";
  const PHONE_SRC = "(?:\\+|00)[0-9]{1,3}[ .-]?[0-9](?:[ .-]?[0-9]){6,12}|0[5-8](?:[ .-]?[0-9]){8}";
  const WORD_SRC = "[0-9A-Za-z" + R(0xc0, 0x24f) + R(0x300, 0x36f) + R(0x621, 0x63a) + R(0x640, 0x65f) +
    R(0x660, 0x669) + R(0x670, 0x6d3) + R(0x6d6, 0x6ed) + R(0x6f0, 0x6f9) + R(0xfb50, 0xfdff) + R(0xfe70, 0xfefc) + "]+";
  const BEFORE_URL = /[A-Za-z0-9_@.-]/;
  const ALNUM = /[A-Za-z0-9]/;
  const TRAILING = ".,;:!?)]}" + C(0xbb) + "\"'" + C(0x2026) + C(0x60c) + C(0x61b) + C(0x61f);

  const AR_MAP = {};
  [[0x629, 0x647], [0x649, 0x64a], [0x671, 0x627], [0x6a9, 0x643], [0x6cc, 0x64a], [0x6ad, 0x643], [0x6af, 0x643],
   [0x6a4, 0x641], [0x67e, 0x628], [0x686, 0x62c], [0x6be, 0x647], [0x6c0, 0x647], [0x6d2, 0x64a], [0x626, 0x64a],
   [0x624, 0x648], [0x623, 0x627], [0x625, 0x627], [0x622, 0x627]].forEach(([a, b]) => { AR_MAP[C(a)] = C(b); });
  AR_MAP[C(0x621)] = "";
  for (let i = 0; i < 10; i++) { AR_MAP[C(0x660 + i)] = String(i); AR_MAP[C(0x6f0 + i)] = String(i); }
  const MARKS_RE = new RegExp("[" + R(0x300, 0x36f) + R(0x610, 0x61a) + R(0x64b, 0x65f) + C(0x670) + R(0x6d6, 0x6ed) + C(0x640) + "]", "g");
  const REPEAT_RE = /(.)\1{2,}/g;
  const DIGITRUN_RE = /[0-9]{2,}/g;
  const AR_RE = new RegExp("^[" + R(0x600, 0x6ff) + "]");
  const DIGIT_WORD = new RegExp("^[0-9" + R(0x660, 0x669) + R(0x6f0, 0x6f9) + "]+$");

  function normalizeToken(tok) {
    let s = tok.normalize("NFKC").toLowerCase();
    s = s.normalize("NFD").replace(MARKS_RE, "").normalize("NFC");
    let o = "";
    for (const ch of s) o += (ch in AR_MAP) ? AR_MAP[ch] : ch;
    return o.replace(REPEAT_RE, "$1$1").replace(DIGITRUN_RE, "0");
  }

  function tokenize(text) {
    text = text || "";
    const spans = [];
    const taken = new Uint8Array(text.length + 1);
    const anyTaken = (s, e) => { for (let k = s; k < e; k++) if (taken[k]) return true; return false; };
    function claim(src, flags, kind) {
      const re = new RegExp(src, flags);
      let m;
      while ((m = re.exec(text)) !== null) {
        if (m[0].length === 0) { re.lastIndex++; continue; }
        let s = m.index, e = m.index + m[0].length;
        if (anyTaken(s, e)) continue;
        const prev = s > 0 ? text[s - 1] : "", nxt = e < text.length ? text[e] : "";
        if (kind === "url" && prev && BEFORE_URL.test(prev)) continue;
        if (kind === "phone" && ((prev && ALNUM.test(prev)) || (nxt && ALNUM.test(nxt)))) continue;
        let raw = text.slice(s, e);
        while (raw && TRAILING.indexOf(raw[raw.length - 1]) >= 0) { raw = raw.slice(0, -1); e -= 1; }
        if (kind === "url" && raw.indexOf(".") < 0) continue;
        if (kind === "phone" && raw.replace(/[^0-9]/g, "").length < 9) continue;
        spans.push([s, e, kind]);
        for (let k = s; k < e; k++) taken[k] = 1;
      }
    }
    claim(URL_SRC, "gi", "url");
    claim(EMAIL_SRC, "g", "email");
    claim(PHONE_SRC, "g", "phone");
    const wre = new RegExp(WORD_SRC, "g");
    let m;
    while ((m = wre.exec(text)) !== null) {
      const s = m.index, e = s + m[0].length;
      if (anyTaken(s, e)) continue;
      spans.push([s, e, "word"]);
    }
    spans.sort((a, b) => a[0] - b[0] || a[1] - b[1] || (a[2] < b[2] ? -1 : a[2] > b[2] ? 1 : 0));
    const toks = [];
    for (const [s, e, kind] of spans) {
      const raw = text.slice(s, e);
      let norm;
      if (kind === "url") norm = "lnk";
      else if (kind === "email") norm = "eml";
      else if (kind === "phone") norm = "tel";
      else { norm = normalizeToken(raw); if (!norm) continue; }
      toks.push({ raw, norm, kind, s, e });
    }
    return toks;
  }

  function ngramFeatures(norms, nmin = 2, nmax = 5) {
    const feats = [];
    for (let i = 0; i < norms.length; i++) {
      const t = norms[i], w = " " + t + " ", L = w.length;
      for (let n = nmin; n <= nmax; n++) {
        if (L < n) { if (n === nmin) feats.push(["c:" + w, i]); break; }
        for (let k = 0; k <= L - n; k++) feats.push(["c:" + w.substr(k, n), i]);
      }
      feats.push(["w:" + t, i]);
      if (i + 1 < norms.length) feats.push(["b:" + t + " " + norms[i + 1], i]);
    }
    return feats;
  }

  // ------------------------------------------------------------------ ML
  class MLModel {
    constructor(d) {
      this.features = new Map(Object.entries(d.features));
      this.intercept = d.intercept;
    }
    score(tokens) {
      const norms = tokens.map((t) => t.norm);
      const counts = new Map(), where = new Map();
      for (const [f, i] of ngramFeatures(norms)) {
        if (this.features.has(f)) {
          counts.set(f, (counts.get(f) || 0) + 1);
          if (!where.has(f)) where.set(f, []);
          where.get(f).push(i);
        }
      }
      const contrib = new Array(tokens.length).fill(0);
      if (counts.size === 0) return [this.intercept, contrib];
      const vals = new Map();
      for (const [f, c] of counts) vals.set(f, (1 + Math.log(c)) * this.features.get(f)[0]);
      let sq = 0;
      for (const v of vals.values()) sq += v * v;
      const norm = Math.sqrt(sq) || 1;
      let logit = this.intercept;
      for (const [f, v] of vals) {
        const c = this.features.get(f)[1] * v / norm;
        logit += c;
        const occ = where.get(f), share = c / occ.length;
        for (const i of occ) contrib[i] += share;
      }
      return [logit, contrib];
    }
  }

  // ------------------------------------------------------------------ helpers
  const sigmoid = (z) => 1 / (1 + Math.exp(-Math.max(-30, Math.min(30, z))));
  const IP_RE = /^[0-9]{1,3}(\.[0-9]{1,3}){3}$/;
  const SCHEME_RE = /^([a-zA-Z][a-zA-Z0-9+.-]*):\/\//;
  const TWO_DIGIT_CC = new Set(["20", "27", "30", "31", "32", "33", "34", "36", "39", "40", "41", "43", "44", "45", "46", "47", "48",
    "49", "51", "52", "53", "54", "55", "56", "57", "58", "60", "61", "62", "63", "64", "65", "66", "81", "82", "84", "86", "90", "91",
    "92", "93", "94", "95", "98"]);
  const HOMO = { "0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "7": "t", "-": "" };
  const homo = (s) => { let o = ""; for (const ch of s) o += (ch in HOMO) ? HOMO[ch] : ch; return o; };

  function osaDistance(a, b, maxd = 3) {
    if (Math.abs(a.length - b.length) > maxd) return maxd + 1;
    let prev2 = null, prev = Array.from({ length: b.length + 1 }, (_, j) => j);
    for (let i = 1; i <= a.length; i++) {
      const cur = [i].concat(new Array(b.length).fill(0));
      for (let j = 1; j <= b.length; j++) {
        const cost = a[i - 1] === b[j - 1] ? 0 : 1;
        cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost);
        if (prev2 !== null && i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) cur[j] = Math.min(cur[j], prev2[j - 2] + 1);
      }
      prev2 = prev; prev = cur;
    }
    return prev[b.length];
  }

  const AR_CLITIC = new Set([0x648, 0x641, 0x628, 0x644, 0x643].map(C)); // و ف ب ل ك
  const AL = C(0x627) + C(0x644), LL = C(0x644) + C(0x644);
  function tokenForms(t) {
    const forms = [t];
    if (AR_RE.test(t)) {
      if (AR_CLITIC.has(t[0]) && t.length > 3) {
        forms.push(t.slice(1));
        if (t.slice(1, 3) === AL && t.length > 4) forms.push(t.slice(3));
      }
      if (t.startsWith(AL) && t.length > 3) forms.push(t.slice(2));
      if (t.startsWith(LL) && t.length > 3) forms.push(t.slice(2));
    } else if (t.length >= 4 && "lfbw".indexOf(t[0]) >= 0) {
      forms.push(t.slice(1));
    }
    return forms;
  }

  function compile(phrases) {
    const idx = new Map(), wild = [];
    for (const p of phrases) {
      const toks = p.split(/\s+/).filter(Boolean).map((w) => w.endsWith("*") ? normalizeToken(w.slice(0, -1)) + "*" : normalizeToken(w))
        .filter((t) => t && t !== "*");
      if (!toks.length) continue;
      if (toks[0].endsWith("*")) wild.push(toks);
      else { if (!idx.has(toks[0])) idx.set(toks[0], []); idx.get(toks[0]).push(toks); }
    }
    return { idx, wild };
  }
  const tokOk = (p, fs) => p.endsWith("*") ? fs.some((f) => f.startsWith(p.slice(0, -1))) : fs.indexOf(p) >= 0;

  // ------------------------------------------------------------------ engine
  class Engine {
    constructor(bundle) {
      this.b = bundle;
      this.kb = bundle.knowledge;
      this.fusion = bundle.fusion;
      this.ml = new MLModel(bundle.ml);
      this.text = this.kb.TEXT;
      this.rules = this.kb.RULES;
      this.concepts = {};
      for (const [name, ph] of Object.entries(this.kb.CONCEPTS)) this.concepts[name] = compile(ph);
      this.brands = this.kb.BRANDS;
      for (const [bid, br] of Object.entries(this.brands)) this.concepts["brand:" + bid] = compile(br.names);
      this.official = [];
      for (const [bid, br] of Object.entries(this.brands)) for (const d of br.official) this.official.push([d, bid]);
      this.officialLabels = new Map();
      for (const [d, bid] of this.official) {
        const lab = d.split(".")[0];
        if (lab.length >= 5 && !this.officialLabels.has(homo(lab))) this.officialLabels.set(homo(lab), [d, bid]);
      }
      this.soft = new Set(this.kb.SOFT_HARM || []);
    }

    _match(forms, comp) {
      const seen = new Set(), spans = [];
      const n = forms.length;
      for (let i = 0; i < n; i++) {
        let cands = [];
        for (const f of forms[i]) { const l = comp.idx.get(f); if (l) cands = cands.concat(l); }
        for (const w of comp.wild) if (tokOk(w[0], forms[i])) cands.push(w);
        for (const ph of cands) {
          const L = ph.length;
          if (i + L > n) continue;
          let ok = true;
          for (let k = 1; k < L; k++) if (!tokOk(ph[k], forms[i + k])) { ok = false; break; }
          if (ok) { const key = i + "," + (i + L); if (!seen.has(key)) { seen.add(key); spans.push([i, i + L]); } }
        }
      }
      spans.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
      return spans;
    }

    _spans(name, ctx) {
      let out = [];
      for (const n of name.split("|")) {
        if (!(n in ctx.cache)) ctx.cache[n] = this._match(ctx.forms, this.concepts[n] || { idx: new Map(), wild: [] });
        out = out.concat(ctx.cache[n]);
      }
      return out;
    }

    _eval(cond, ctx) {
      if ("has" in cond) return this._spans(cond.has, ctx).length > 0;
      if ("flag" in cond) return !!ctx.flags[cond.flag];
      if ("not" in cond) return !this._eval(cond.not, ctx);
      if ("all" in cond) return cond.all.every((c) => this._eval(c, ctx));
      if ("any" in cond) return cond.any.some((c) => this._eval(c, ctx));
      if ("near" in cond) {
        const [a, b, w] = cond.near;
        const A = this._spans(a, ctx), B = this._spans(b, ctx);
        for (const [s1, e1] of A) for (const [s2, e2] of B) {
          const gap = e1 <= s2 ? s2 - e1 : (e2 <= s1 ? s1 - e2 : 0);
          if (gap <= w) return true;
        }
        return false;
      }
      throw new Error("bad condition " + JSON.stringify(cond));
    }

    _hostIs(host, domains) {
      for (const d of domains) if (host === d || host.endsWith("." + d)) return d;
      return null;
    }

    analyzeLink(raw) {
      const s = raw.trim();
      const m = s.match(SCHEME_RE);
      const scheme = m ? m[1].toLowerCase() : "";
      const rest = m ? s.slice(m[0].length) : s;
      let host = rest.split(/[\/?#]/)[0];
      if (host.indexOf("@") >= 0) host = host.slice(host.lastIndexOf("@") + 1);
      host = host.split(":")[0].toLowerCase().replace(/^\.+|\.+$/g, "");
      if (host.startsWith("www.")) host = host.slice(4);
      const labels = host.split(".");
      const suffix2 = labels.slice(-2).join(".");
      const registered = (this.kb.MULTI_SUFFIXES.indexOf(suffix2) >= 0 && labels.length >= 3) ? labels.slice(-3).join(".") : suffix2;
      const tld = labels.length ? labels[labels.length - 1] : "";
      const info = { raw, host, registered, tld, flags: [], status: "unknown", brand: null, official: null };
      const flags = info.flags;
      if (this._hostIs(host, this.kb.CHAT_HOSTS)) { flags.push("chat"); info.status = "chat"; return info; }
      let off = null;
      for (const [d, bid] of this.official) if (host === d || host.endsWith("." + d)) { off = [d, bid]; break; }
      if (off === null && this._hostIs(host, this.kb.OFFICIAL_SUFFIXES)) off = [registered, "royaume"];
      if (off) {
        info.status = "official"; info.brand = off[1]; info.official = off[0];
        if (scheme === "http") flags.push("http");
        return info;
      }
      if (this._hostIs(host, this.kb.REPUTABLE)) { info.status = "reputable"; return info; }
      if (IP_RE.test(host)) flags.push("ip");
      if (host.indexOf("xn--") >= 0) flags.push("punycode");
      if (this._hostIs(host, this.kb.SHORTENERS)) flags.push("shortener");
      if (this._hostIs(host, this.kb.FREEHOST)) flags.push("freehost");
      if (this.kb.SUS_TLDS.indexOf(tld) >= 0) flags.push("susp_tld");
      if (scheme === "http") flags.push("http");
      for (const [d, bid] of this.official.concat([["gov.ma", "royaume"]])) {
        if (host.startsWith(d + ".") || host.indexOf("." + d + ".") >= 0) { flags.push("decoy"); info.brand = bid; info.official = d; break; }
      }
      if (flags.indexOf("decoy") < 0 && flags.indexOf("shortener") < 0 && flags.indexOf("ip") < 0) {
        const parts = host.split(/[.\-_]/);
        for (const [bid, br] of Object.entries(this.brands)) {
          let hit = false;
          for (const kw of br.kw) if ((kw.length >= 4 && host.indexOf(kw) >= 0) || parts.indexOf(kw) >= 0) { hit = true; break; }
          if (hit) { flags.push("impersonation"); info.brand = bid; info.official = br.official.length ? br.official[0] : ".gov.ma"; break; }
        }
        if (flags.indexOf("impersonation") < 0) {
          const lab = homo(registered.split(".")[0]);
          if (lab.length >= 5) {
            for (const [olab, [d, bid]] of this.officialLabels) {
              const dist = osaDistance(lab, olab, 2);
              if (dist > 0 && dist <= (olab.length < 9 ? 1 : 2)) { flags.push("typosquat"); info.brand = bid; info.official = d; break; }
            }
          }
        }
      }
      info.status = (flags.length && !(flags.length === 1 && flags[0] === "http")) ? "suspicious" : "unknown";
      return info;
    }

    static analyzeSender(sender) {
      const out = { raw: sender || "", kind: "none", foreign: false, prefix: "" };
      if (!sender || !sender.trim()) return out;
      const s = sender.trim();
      const digits = s.replace(/[^0-9]/g, "");
      if (digits.length >= 8 && s.replace(/[0-9\s+().-]/g, "").length === 0) {
        const intl = s.startsWith("+") || s.startsWith("00");
        const d = s.startsWith("00") ? digits.slice(2) : digits;
        if (intl && !d.startsWith("212")) {
          const n = "17".indexOf(d[0]) >= 0 ? 1 : (TWO_DIGIT_CC.has(d.slice(0, 2)) ? 2 : 3);
          out.kind = "phone"; out.foreign = true; out.prefix = "+" + d.slice(0, n);
        } else { out.kind = "phone"; out.prefix = "+212"; }
      } else out.kind = "alpha";
      return out;
    }

    analyze(text, sender) {
      const t0 = (typeof performance !== "undefined" ? performance : Date).now();
      const toks = tokenize(text || "");
      const forms = toks.map((t) => tokenForms(t.norm));
      const ctx = { forms, cache: {}, flags: {} };
      const F = ctx.flags;
      const links = toks.filter((t) => t.kind === "url").map((t) => this.analyzeLink(t.raw));
      const nonoff = links.filter((l) => l.status !== "official" && l.status !== "reputable");
      F.has_link = links.length > 0;
      F.link_nonofficial = nonoff.length > 0;
      F.link_unknown = nonoff.length > 0;
      F.link_official_only = links.length > 0 && links.every((l) => l.status === "official");
      F.link_nonofficial_foreign = nonoff.some((l) => !l.registered.endsWith(".ma"));
      F.link_unknown_ma = nonoff.some((l) => l.registered.endsWith(".ma"));
      for (const fl of ["ip", "punycode", "shortener", "chat", "freehost", "susp_tld", "http", "decoy", "impersonation", "typosquat"])
        F["link_" + fl] = links.some((l) => l.flags.indexOf(fl) >= 0);
      const chatCc = links.filter((l) => l.status === "chat" && l.host.indexOf("wa.me") >= 0)
        .map((l) => { const i = l.raw.indexOf("/"); return (i >= 0 ? l.raw.slice(i + 1) : l.raw).replace(/[^0-9]/g, ""); });
      const foreignChat = chatCc.filter((d) => d.length >= 8 && !d.startsWith("212") && !d.startsWith("0"));
      F.link_chat_foreign = foreignChat.length > 0;
      const mentioned = Object.keys(this.brands).filter((bid) => this._spans("brand:" + bid, ctx).length > 0);
      const cats = new Set(mentioned.map((b) => this.brands[b].cat));
      F.claims_gov = cats.has("gov") || this._spans("FINE", ctx).length > 0;
      F.claims_bank = cats.has("bank") || this._spans("BANK_GENERIC", ctx).length > 0;
      F.claims_telco = cats.has("telco");
      F.claims_post = cats.has("post");
      const specific = mentioned.filter((b) => this.brands[b].official.length > 0);
      const webBad = nonoff.filter((l) => l.status === "suspicious" || l.status === "unknown");
      F.brand_link_mismatch = specific.length > 0 && webBad.length > 0;
      const snd = Engine.analyzeSender(sender);
      F.sender_foreign = snd.foreign;
      F.has_phone = toks.some((t) => t.kind === "phone" || (t.kind === "word" && DIGIT_WORD.test(t.raw) && t.raw.length >= 9));
      F.phone_foreign = toks.some((t) => t.kind === "phone" && (t.raw.trim().startsWith("+") || t.raw.trim().startsWith("00")) &&
        !t.raw.replace(/[^0-9]/g, "").replace(/^0+/, "").startsWith("212"));
      const [logit, contrib] = this.ml.score(toks);
      const pMl = sigmoid(logit);
      const fired = [], best = {};
      for (const r of this.rules) {
        if (this._eval(r.when, ctx)) {
          let crit = r.critical || false;
          if (typeof crit === "object") crit = this._eval(crit, ctx);
          fired.push({ id: r.id, w: r.w, group: r.group, harm: !!r.harm, critical: !!crit, safe: !!r.safe, hl: r.hl || [], floor: r.floor || 0 });
        }
      }
      for (const f of fired) if (!(f.group in best) || Math.abs(f.w) > Math.abs(best[f.group])) best[f.group] = f.w;
      const fz = this.fusion;
      let S = 0;
      for (const v of Object.values(best)) S += v;
      let risk = sigmoid(fz.a * logit + fz.b + S);
      const harm = fired.some((f) => f.harm);
      const strong = fired.some((f) => f.harm && !this.soft.has(f.id));
      const critical = fired.some((f) => f.critical);
      if (critical) risk = Math.max(risk, fz.floor_critical);
      else if (!harm) risk = Math.min(risk, fz.cap_no_harm);
      if (harm && !strong && !critical) risk = Math.min(risk, fz.t_red - 0.01);
      const safe = fired.some((f) => f.safe);
      if (!harm && !critical && !safe && pMl >= (fz.ml_alone === undefined ? 2 : fz.ml_alone))
        risk = Math.min(Math.max(risk, fz.ml_alone_floor === undefined ? 0.5 : fz.ml_alone_floor), fz.t_red - 0.01);
      for (const f of fired) risk = Math.max(risk, f.floor);
      const verdict = risk >= fz.t_red ? "red" : (risk >= fz.t_amber ? "amber" : "green");
      const bad = links.find((l) => l.status === "suspicious") || webBad[0] || nonoff[0] || null;
      const offl = links.find((l) => l.status === "official") || null;
      const params = { domain: (bad || offl || {}).host || "", tld: (bad || {}).tld || "",
        prefix: snd.prefix || (foreignChat.length ? "+" + foreignChat[0].slice(0, 3) : "") };
      const lb = (bad && bad.brand) ? bad.brand : (specific[0] || null);
      if (lb) {
        params.brand = this.brands[lb].label;
        params.official = (bad && bad.official) || (this.brands[lb].official.length ? this.brands[lb].official[0] : ".gov.ma");
      }
      if (offl) { if (!("official" in params)) params.official = offl.host; if (!bad) params.domain = offl.host; }
      const hl = [];
      for (const f of fired) {
        if (f.safe) continue;
        for (const c of f.hl) for (const [s, e] of this._spans(c, ctx)) hl.push({ s: toks[s].s, e: toks[e - 1].e, kind: "rule", rule: f.id });
      }
      for (const t of toks) if (t.kind === "url") {
        const li = links.find((l) => l.raw === t.raw);
        if (["suspicious", "unknown", "chat"].indexOf(li.status) >= 0) hl.push({ s: t.s, e: t.e, kind: "link", rule: "link" });
      }
      if (pMl >= 0.5) {
        const ranked = toks.map((_, i) => i).sort((i, j) => contrib[j] - contrib[i]);
        for (const i of ranked.slice(0, 4)) if (contrib[i] > 0.12 && toks[i].kind === "word")
          hl.push({ s: toks[i].s, e: toks[i].e, kind: "ml", rule: "ml", score: Math.round(contrib[i] * 1000) / 1000 });
      }
      let stype = null;
      if (verdict !== "green") {
        const firedIds = new Set(fired.map((f) => f.id));
        let top = null, topScore = -1;
        for (const [typ, sig] of Object.entries(this.kb.TYPES)) {
          let sc = 0;
          for (const [key, w] of Object.entries(sig)) {
            if (key.startsWith("rule:")) sc += firedIds.has(key.slice(5)) ? w : 0;
            else if (key.startsWith("flag:")) sc += F[key.slice(5)] ? w : 0;
            else if (key.startsWith("cat:")) sc += cats.has(key.slice(4)) ? w : 0;
            else if (key.startsWith("brand:")) sc += mentioned.indexOf(key.slice(6)) >= 0 ? w : 0;
            else sc += this._spans(key, ctx).length ? w : 0;
          }
          if (sc > topScore) { top = typ; topScore = sc; }
        }
        stype = topScore >= 2 ? top : "generic";
      }
      const signals = fired.map((f) => ({ id: f.id, w: f.w, critical: f.critical, safe: f.safe, harm: f.harm }));
      signals.sort((a, b) => (a.critical === b.critical ? 0 : (a.critical ? -1 : 1)) || (Math.abs(b.w) - Math.abs(a.w)));
      const t1 = (typeof performance !== "undefined" ? performance : Date).now();
      return {
        risk: Math.round(risk * 1e4) / 1e4, verdict, type: stype,
        ml: { prob: Math.round(pMl * 1e4) / 1e4, logit: Math.round(logit * 1e4) / 1e4 },
        signals, params, links, sender: snd, highlights: hl, n_tokens: toks.length,
        components: { S: Math.round(S * 1e4) / 1e4, harm, strong, critical, safe, floor: Math.max(0, ...fired.map((f) => f.floor)) },
        latency_ms: Math.round((t1 - t0) * 1000) / 1000, _risk_raw: risk, _logit_raw: logit,
      };
    }

    explain(r, lang) {
      const T = this.text;
      const tr = (key, kw) => {
        let s = (T[key] && (T[key][lang] || T[key].en)) || key;
        for (const [k, v] of Object.entries(kw || {})) s = s.split("{" + k + "}").join(String(v));
        return s;
      };
      const reasons = [];
      const fired = new Set(r.signals.map((x) => x.id));
      const red = this.kb.REDUNDANT || {};
      const maxR = this.kb.MAX_REASONS === undefined ? 99 : this.kb.MAX_REASONS;
      let shown = 0;
      for (const s of r.signals) {
        if (s.id === "link_unknown" && r.signals.some((x) => x.id.startsWith("link_") && x.id !== "link_unknown" && !x.safe)) continue;
        if ((red[s.id] || []).some((o) => fired.has(o))) continue;
        if (!s.safe) { if (shown >= maxR) continue; shown += 1; }
        reasons.push({ id: s.id, safe: s.safe, critical: s.critical, text: tr(s.id, r.params) });
      }
      if (r.ml.prob >= 0.8 && r.verdict !== "green") reasons.push({ id: "ml_high", safe: false, critical: false, text: tr("ml_high") });
      if (!r.signals.some((s) => s.harm)) reasons.push({ id: "no_harm", safe: true, critical: false, text: tr("no_harm") });
      const typ = r.type;
      return {
        verdict: tr("verdict_" + r.verdict),
        type: typ ? tr("type_" + typ) : null,
        reasons,
        do: tr("do_" + r.verdict),
        tip: typ ? tr("tip_" + typ) : null,
        if_victim: r.verdict !== "green" ? tr("if_victim") : null,
        share: (r.verdict === "red" && typ) ? tr("share_warning", { type: tr("type_" + typ) }) : null,
      };
    }
  }

  const api = { Engine, tokenize, normalizeToken, ngramFeatures, MLModel, version: "0.4.0" };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.ReddLbal = api;
})(typeof window !== "undefined" ? window : globalThis);
