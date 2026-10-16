"""
Parity test: the JavaScript engine (phone/browser) must give the SAME answers as the
Python engine (LinuxONE API). Run:  python tests/parity_test.py
"""
import json
import os
import subprocess
import sys
import tempfile

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from engine.core import Engine  # noqa: E402
from engine.text import tokenize  # noqa: E402

EDGE = [
    ("📦 Votre colis est bloqué, réglez 12,99 DH : bit.ly/abc  — +44 7520 113 284 / 0661234567", ""),
    ("سلام ماما 😂😂 هادي نمرة جديدة ديالي، عافاك صيفطي ليا 500 درهم فوفاكاش", "+33 6 12 34 56 78"),
    ("ﷺ ﻻ إله إلا الله — أدّوا الغرامة قبل ٢٤ ساعة: https://justice-amendes.icu/v/٤٤٧١", "+63 917 552 0193"),
    ("Mr.Ali e.g. www.cnss.ma) rh@jobs-canada.com wa.me/447700900123 http://185.23.44.12/cih/login", "CIH BANK"),
    ("cihbank.ma.secure-x.top/login attijariwafabnk.com xn--cihbnk-9ua.com", ""),
    ("", ""), ("   ", ""), ("سلااااام", ""), ("SAAAALAM KHOUYA", ""),
]

if __name__ == "__main__":
    bundle = os.path.join(ROOT, "model", "redd_lbal.json")
    eng = Engine(bundle)
    items = list(EDGE)
    for n in ["challenge_set", "blind_set", "blind_set2"]:
        d = pd.read_csv(os.path.join(ROOT, "data", f"{n}.csv"), keep_default_na=False)
        items += list(zip(d.text, d.sender))
    te = pd.read_csv(os.path.join(ROOT, "data", "processed", "test.csv")).sample(1500, random_state=3)
    items += [(t, "") for t in te.text.astype(str)]
    py = []
    for text, sender in items:
        r = eng.analyze(text, sender or None)
        py.append({"tokens": [[t["raw"], t["norm"], t["kind"], t["s"], t["e"]] for t in tokenize(text)],
                   "logit": r["ml"]["logit"], "risk": r["risk"], "verdict": r["verdict"], "type": r["type"],
                   "signals": [s["id"] for s in r["signals"]],
                   "hl": [[h["s"], h["e"], h["rule"]] for h in r["highlights"] if h["kind"] != "ml"],
                   "explain_dar": [x["text"] for x in eng.explain(r, "dar")["reasons"]]})
    with tempfile.TemporaryDirectory() as td:
        inp, outp = os.path.join(td, "in.json"), os.path.join(td, "out.json")
        with open(inp, "w", encoding="utf-8") as fh:
            json.dump(items, fh, ensure_ascii=False)
        subprocess.run(["node", os.path.join(ROOT, "tests", "parity_node.js"), bundle, inp, outp], check=True)
        with open(outp, encoding="utf-8") as fh:
            js = json.load(fh)
    bad = 0
    for (text, _), p, j in zip(items, py, js):
        errs = []
        if p["tokens"] != j["tokens"]:
            errs.append(("tokens", p["tokens"], j["tokens"]))
        if abs(p["logit"] - j["logit"]) > 1e-3:
            errs.append(("logit", p["logit"], j["logit"]))
        if abs(p["risk"] - j["risk"]) > 1e-3:
            errs.append(("risk", p["risk"], j["risk"]))
        for k in ["verdict", "type", "signals", "hl", "explain_dar"]:
            if p[k] != j[k]:
                errs.append((k, p[k], j[k]))
        if errs:
            bad += 1
            if bad <= 5:
                print("MISMATCH:", text[:90])
                for e in errs:
                    print("   ", str(e)[:400])
    print(f"parity: {len(items) - bad}/{len(items)} messages identical")
    sys.exit(1 if bad else 0)
