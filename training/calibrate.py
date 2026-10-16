"""
Fuse Brain 1 (ML) and Brain 2 (rules) - calibrate on a DEV split carved from train.csv.

  risk = sigmoid(a * ml_logit + b + sum(rule weights))
  + critical rules  -> risk >= floor_critical
  + no attack vector -> risk < t_amber (a message that asks nothing can't harm you)
  + AI-alone safety net: very confident AI with no attack vector -> "suspicious", never "scam"

We grid-search (a, b, thresholds, AI-alone threshold) to catch as many dev scams as
possible while keeping false alarms on REAL Moroccan messages near zero.
Writes model/fusion.json.  Run:  python training/calibrate.py
"""
import itertools
import json
import os
import random
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "training"))
from engine import export  # noqa: E402
from engine.core import Engine  # noqa: E402
from train_ml import export as export_ml, fit, sample_weights  # noqa: E402

SEED = 7


def split_dev(tr):
    rng = random.Random(SEED)
    tids = sorted(t for t in tr["template_id"].dropna().unique() if t)
    dev_t = set(rng.sample(tids, int(len(tids) * 0.2)))
    is_syn = tr["template_id"].fillna("").astype(str).str.len() > 0
    dev = np.where(is_syn, tr["template_id"].isin(dev_t), np.array([rng.random() < 0.12 for _ in range(len(tr))]))
    return tr[~dev], tr[dev]


def components(engine, df):
    rows = []
    for t, s in zip(df["text"].astype(str), df.get("sender", pd.Series([None] * len(df))).fillna("")):
        r = engine.analyze(t, s or None)
        c = r["components"]
        rows.append((r["ml"]["logit"], r["ml"]["prob"], c["S"], c["harm"], c["strong"], c["critical"], c["safe"], c["floor"]))
    return pd.DataFrame(rows, columns=["logit", "p_ml", "S", "harm", "strong", "critical", "safe", "floor"], index=df.index)


def fuse(C, a, b, t_amber, t_red, ml_alone, floor_crit=0.93):
    z = a * C["logit"].values + b + C["S"].values
    risk = 1 / (1 + np.exp(-np.clip(z, -30, 30)))
    crit, harm, safe = C["critical"].values, C["harm"].values, C["safe"].values
    risk = np.where(crit, np.maximum(risk, floor_crit), np.where(~harm, np.minimum(risk, t_amber - 0.01), risk))
    risk = np.where(harm & ~C["strong"].values & ~crit, np.minimum(risk, t_red - 0.01), risk)
    alone = (~harm) & (~crit) & (~safe) & (C["p_ml"].values >= ml_alone)
    risk = np.where(alone, np.minimum(np.maximum(risk, max(0.5, t_amber)), t_red - 0.01), risk)
    risk = np.maximum(risk, C["floor"].values)
    return np.where(risk >= t_red, 2, np.where(risk >= t_amber, 1, 0))


if __name__ == "__main__":
    tr = pd.read_csv(os.path.join(ROOT, "data", "processed", "train.csv"))
    fit_df, dev = split_dev(tr)
    print(f"fit={len(fit_df):,}  dev={len(dev):,} (dev scams={int(dev.label.sum())})")
    tmp_ml = os.path.join(ROOT, "model", "_ml_dev.json")
    tmp_bundle = os.path.join(ROOT, "model", "_bundle_dev.json")
    if "--reuse" not in sys.argv or not os.path.exists(tmp_ml):
        vec, clf = fit(fit_df["text"].astype(str).tolist(), fit_df["label"].values, sample_weights(fit_df))
        export_ml(vec, clf, tmp_ml)
    export.build(tmp_ml, tmp_bundle, fusion=export.DEFAULT_FUSION)
    eng = Engine(tmp_bundle)
    C = components(eng, dev)
    dev = dev.assign(**{c: C[c].values for c in C.columns})
    y = dev["label"].values
    real = dev["source"].isin(["doda", "doda_en", "myc", "mac", "uci"]).values & (y == 0)
    syn_legit = dev["source"].str.startswith("synthetic").values & (y == 0)
    scam = y == 1
    best = None
    # The rules were written by people who saw these templates, so dev over-rates them: we keep a
    # meaningful weight on the ML brain (a >= 0.5) and value catching scams (amber or red) highly,
    # because a missed scam costs far more than a "please verify" on a normal message.
    grid = itertools.product([0.5, 0.6, 0.75, 0.9, 1.0], [-3, -2.5, -2, -1.5, -1, -0.5, 0, 0.5],
                             [0.35, 0.4, 0.45, 0.5], [0.65, 0.7, 0.75, 0.8], [0.9, 0.95, 0.97, 0.99, 2.0])
    for a, b, ta, trd, mla in grid:
        v = fuse(C, a, b, ta, trd, mla)
        m = {"rec_red": (v[scam] == 2).mean(), "rec_flag": (v[scam] >= 1).mean(),
             "fpr_red_real": (v[real] == 2).mean(), "fpr_flag_real": (v[real] >= 1).mean(),
             "fpr_red_syn": (v[syn_legit] == 2).mean(), "fpr_flag_syn": (v[syn_legit] >= 1).mean()}
        if m["fpr_red_real"] > 0.002 or m["fpr_flag_real"] > 0.01 or m["fpr_red_syn"] > 0.03:
            continue
        score = m["rec_red"] + 1.0 * m["rec_flag"] - 1 * m["fpr_flag_syn"] - 5 * m["fpr_red_syn"] - 10 * m["fpr_flag_real"]
        if best is None or score > best[0]:
            best = (score, dict(a=a, b=b, t_amber=ta, t_red=trd, ml_alone=mla), m)
    if best is None or "--debug" in sys.argv:
        v = fuse(C, 0.6, -1.0, 0.4, 0.75, 2.0)
        dev["v"] = v
        bad = dev[(dev.label == 0) & (dev.v >= 1)]
        print("legit flagged by source:", bad.groupby("source").size().to_dict(), "of", dev[dev.label == 0].groupby("source").size().to_dict())
        pd.set_option("display.width", 250)
        print(bad.sample(min(25, len(bad)), random_state=1)[["source", "campaign", "p_ml", "S", "harm", "critical", "text"]].to_string(max_colwidth=90))
        miss = dev[(dev.label == 1) & (dev.v == 0)]
        print("scams missed by campaign:", miss.groupby("campaign").size().to_dict())
        print(miss.sample(min(15, len(miss)), random_state=1)[["campaign", "p_ml", "S", "harm", "text"]].to_string(max_colwidth=90))
        if best is None:
            sys.exit(1)
    score, params, m = best
    fusion = {**export.DEFAULT_FUSION, **params, "cap_no_harm": params["t_amber"] - 0.01,
              "ml_alone_floor": max(0.5, params["t_amber"])}
    with open(os.path.join(ROOT, "model", "fusion.json"), "w") as fh:
        json.dump(fusion, fh, indent=2)
    print("best fusion:", json.dumps(fusion))
    print("dev metrics:", {k: round(float(v), 4) for k, v in m.items()})
    os.remove(tmp_bundle)
