"""
Leave-one-campaign-out: can Redd Lbal catch a scam TYPE it has never seen?
For each campaign we retrain the ML brain WITHOUT any message of that campaign,
then test the full engine on that campaign's held-out messages.
(The rules still encode general red flags - links, codes, money, pressure - which is the point.)

Run:  python training/loco.py   (~15 min)  ->  reports/loco.json
"""
import json
import math
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "training"))
from engine import export  # noqa: E402
from engine.core import Engine  # noqa: E402
from train_ml import export as export_ml, fit, sample_weights  # noqa: E402

if __name__ == "__main__":
    tr = pd.read_csv(os.path.join(ROOT, "data", "processed", "train.csv"))
    te = pd.read_csv(os.path.join(ROOT, "data", "processed", "test.csv"))
    camps = sorted(c for c in te[(te.source == "synthetic") & (te.label == 1)].campaign.unique())
    out = {}
    for c in camps:
        sub = tr[tr.campaign != c]
        vec, clf = fit(sub["text"].astype(str).tolist(), sub["label"].values, sample_weights(sub))
        mlp, bp = os.path.join(ROOT, "model", "_loco_ml.json"), os.path.join(ROOT, "model", "_loco_bundle.json")
        export_ml(vec, clf, mlp)
        export.build(mlp, bp)
        eng = Engine(bp)
        test_c = te[(te.campaign == c) & (te.label == 1)]
        v, ml_hit = [], []
        for t in test_c.text.astype(str):
            r = eng.analyze(t)
            v.append(r["verdict"])
            ml_hit.append(r["ml"]["prob"] >= 0.5)
        v = pd.Series(v)
        out[c] = {"n": len(v), "engine_red": float((v == "red").mean()), "engine_flagged": float((v != "green").mean()),
                  "ml_only_caught": float(sum(ml_hit) / len(ml_hit))}
        print(c, out[c], flush=True)
        with open(os.path.join(ROOT, "reports", "loco.json"), "w") as fh:
            json.dump(out, fh, indent=2)
    for f in ("_loco_ml.json", "_loco_bundle.json"):
        os.remove(os.path.join(ROOT, "model", f))
    print("done")
