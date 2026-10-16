"""
Brain 1: the machine-learning model.

char n-grams (2-5, inside words) + word uni/bigrams -> TF-IDF -> Logistic Regression.
Why this model:
  * char n-grams make "3afak / afak / عافاك / 3fak" look alike, and survive typos
  * logistic regression is linear -> every word's contribution can be shown to the
    user (explainability), and inference is a dictionary lookup + dot product:
    microseconds, no numpy needed on LinuxONE (s390x) or in the browser.

Exports model/ml.json (vocabulary, idf, weights) used by engine/core.py and webapp/engine.js.

Run:  python training/train_ml.py            (full fit on train.csv -> model/ml.json)
      python training/train_ml.py --holdout traffic_fine   (leave-one-campaign-out)
"""
import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from engine.text import analyzer  # noqa: E402

VOCAB_SIZE = 40000   # keep the strongest features -> ~1.5 MB JSON for the phone


def fit(texts, labels, weights=None, vocab_size=VOCAB_SIZE, C=4.0):
    t0 = time.time()
    vec = TfidfVectorizer(analyzer=analyzer, sublinear_tf=True, min_df=3, dtype=np.float32)
    X = vec.fit_transform(texts)
    clf = LogisticRegression(C=C, class_weight="balanced", max_iter=3000, solver="liblinear")
    clf.fit(X, labels, sample_weight=weights)
    # keep the top-|weight x idf| features, then refit on that fixed vocabulary (exact, no approximation)
    inv = np.empty(len(vec.vocabulary_), dtype=object)
    for f, i in vec.vocabulary_.items():
        inv[i] = f
    imp = np.abs(clf.coef_[0]) * vec.idf_
    keep = inv[np.argsort(-imp)[:vocab_size]]
    vec2 = TfidfVectorizer(analyzer=analyzer, sublinear_tf=True, vocabulary=list(keep), dtype=np.float32)
    X2 = vec2.fit_transform(texts)
    # idf must come from the full corpus statistics of the kept features
    clf2 = LogisticRegression(C=C, class_weight="balanced", max_iter=3000, solver="liblinear")
    clf2.fit(X2, labels, sample_weight=weights)
    print(f"  fit: {X.shape[1]:,} features -> kept {len(keep):,} | {time.time() - t0:.0f}s")
    return vec2, clf2


def export(vec, clf, path):
    vocab = {f: [round(float(vec.idf_[i]), 5), round(float(clf.coef_[0][i]), 5)] for f, i in vec.vocabulary_.items()}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"type": "tfidf-logreg", "ngram": [2, 5], "sublinear_tf": True,
                   "intercept": round(float(clf.intercept_[0]), 6), "features": vocab}, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"  exported {path} ({os.path.getsize(path) / 1e6:.2f} MB)")


def sample_weights(df):
    # hard negatives (legit look-alikes) and Moroccan scams count more than generic English spam
    w = np.ones(len(df))
    w[(df["source"] == "synthetic") & (df["label"] == 0)] = 3.0
    w[(df["source"] == "uci") & (df["label"] == 1)] = 0.5
    return w


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--holdout", help="campaign to exclude from training (leave-one-campaign-out)")
    ap.add_argument("--out", default=os.path.join(ROOT, "model", "ml.json"))
    args = ap.parse_args()
    tr = pd.read_csv(os.path.join(ROOT, "data", "processed", "train.csv"))
    if args.holdout:
        tr = tr[tr["campaign"] != args.holdout]
    print(f"training on {len(tr):,} messages ({int(tr.label.sum()):,} scams)")
    vec, clf = fit(tr["text"].astype(str).tolist(), tr["label"].values, sample_weights(tr))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    export(vec, clf, args.out)
