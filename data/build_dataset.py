"""
Assemble the Redd Lbal training/test data.

REAL data (human-written):
  - DODa  : ~49k Darija sentences, each in Latin script + Arabic script     (normal)
            github.com/darija-open-dataset/dataset  (research/educational use)
  - MYC   : ~20k Moroccan YouTube comments, both scripts, emoji, code-switch (normal)
            github.com/MouadJb/MYC
  - MAC   : ~18k Moroccan tweets, MSA + Darija                                (normal)
            github.com/LeMGarouani/MAC
  - UCI   : 5.5k English SMS (ham / spam)                                     (normal / scam)
SYNTHETIC data (data/generator.py), split BY TEMPLATE so the test set only
contains wordings the model never saw during training.

Optional, picked up automatically if present:
  - data/raw/vish_darija/*.json  (VISH-DARIJA-TTS text layer -> scammer turns)
  - data/real_messages.csv       (your collected messages; TEST ONLY, never trained on)

Run:  python data/build_dataset.py
"""
import glob
import json
import math
import os
import random

import pandas as pd

from generator import CHAT_LINES, LEGIT_TEMPLATES, SCAM_TEMPLATES, generate

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
OUT = os.path.join(HERE, "processed")
SEED = 42


def template_split(templates, prefix, holdout=0.22, seed=SEED):
    """Hold out whole templates (per campaign) for testing."""
    rng = random.Random(seed)
    by_c = {}
    for i, (c, _, _) in enumerate(templates):
        by_c.setdefault(c, []).append(f"{prefix}{i:03d}")
    test_ids = set()
    for c, ids in by_c.items():
        if len(ids) >= 3:
            k = max(1, round(len(ids) * holdout))
            test_ids.update(rng.sample(ids, k))
    return test_ids


def synthetic():
    rows = []
    # balance campaigns: ~460 scams per campaign, ~260 legit per category
    for scam, templates, target, seed in [(True, SCAM_TEMPLATES, 460, 1), (False, LEGIT_TEMPLATES, 260, 2)]:
        per_c = pd.Series([t[0] for t in templates]).value_counts().to_dict()
        for c, n_t in per_c.items():
            sub = [t for t in templates if t[0] == c]
            n = max(25, math.ceil(target / n_t))
            gen = generate(sub, n, seed + hash(c) % 1000, scam)
            # re-map template ids to the global index
            local_to_global = {f"{'S' if scam else 'L'}{j:03d}": f"{'S' if scam else 'L'}{templates.index(t):03d}"
                               for j, t in enumerate(sub)}
            for r in gen:
                r["template_id"] = local_to_global[r["template_id"]]
            rows += gen
    df = pd.DataFrame(rows)
    test_ids = template_split(SCAM_TEMPLATES, "S") | template_split(LEGIT_TEMPLATES, "L")
    df["split"] = df["template_id"].map(lambda t: "test" if t in test_ids else "train")
    chat = pd.DataFrame({"text": CHAT_LINES, "label": 0, "campaign": "chat", "lang": "mixed",
                         "template_id": "", "source": "synthetic_chat"})
    chat["split"] = "train"
    return pd.concat([df, chat], ignore_index=True)


def real_normals():
    rng = random.Random(SEED)
    parts = []
    # DODa: keep both scripts of a sentence in the same split (no leakage)
    d = pd.read_csv(os.path.join(RAW, "doda_sentences.csv")).dropna(subset=["darija", "darija_ar"])
    d["split"] = [("test" if rng.random() < 0.15 else "train") for _ in range(len(d))]
    parts.append(pd.DataFrame({"text": d["darija"], "lang": "dar_lat", "split": d["split"]}).assign(source="doda"))
    parts.append(pd.DataFrame({"text": d["darija_ar"], "lang": "dar_ar", "split": d["split"]}).assign(source="doda"))
    eng = d.sample(6000, random_state=SEED)
    parts.append(pd.DataFrame({"text": eng["eng"], "lang": "en", "split": eng["split"]}).assign(source="doda_en"))
    # MYC YouTube comments
    y = pd.read_csv(os.path.join(RAW, "myc_youtube_utf16.csv"), encoding="utf-16").dropna(subset=["sentence"])
    y["text"] = y["sentence"].astype(str).str.replace("<br>", " ", regex=False).str.replace("&quot;", '"', regex=False).str.strip('" ')
    y["split"] = [("test" if rng.random() < 0.15 else "train") for _ in range(len(y))]
    parts.append(y[["text", "split"]].assign(lang="mixed", source="myc"))
    # MAC tweets
    m = pd.read_csv(os.path.join(RAW, "mac_tweets.csv")).dropna(subset=["tweets"])
    m["split"] = [("test" if rng.random() < 0.15 else "train") for _ in range(len(m))]
    m["lang"] = m["class"].map(lambda c: "msa" if c == "standard" else "dar_ar")
    parts.append(m.rename(columns={"tweets": "text"})[["text", "split", "lang"]].assign(source="mac"))
    df = pd.concat(parts, ignore_index=True)
    df["label"], df["campaign"], df["template_id"] = 0, "real_normal", ""
    return df


def uci():
    s = pd.read_csv(os.path.join(RAW, "uci_sms.csv"), encoding="latin1")[["v1", "v2"]]
    rng = random.Random(SEED)
    return pd.DataFrame({
        "text": s["v2"], "label": (s["v1"] == "spam").astype(int),
        "campaign": s["v1"].map({"spam": "uci_spam", "ham": "real_normal"}), "lang": "en",
        "template_id": "", "source": "uci", "split": [("test" if rng.random() < 0.2 else "train") for _ in range(len(s))],
    })


def vish_darija():
    """Optional: VISH-DARIJA-TTS text layer (download from Zenodo yourself).
    Uses only the SCAMMER turns of scam scenarios as scam, and all turns of
    non-scam scenarios as normal. Field names may need adjusting."""
    files = glob.glob(os.path.join(RAW, "vish_darija", "**", "*.json"), recursive=True)
    rows = []
    for f in files:
        with open(f, encoding="utf-8") as fh:
            data = json.load(fh)
        scenarios = data if isinstance(data, list) else data.get("scenarios", [data])
        for sc in scenarios:
            is_scam = int(bool(sc.get("is_scam", sc.get("label", 0))))
            for turn in sc.get("turns", []):
                spk = str(turn.get("speaker", "")).lower()
                if is_scam and not any(k in spk for k in ("scam", "fraud", "caller", "attacker")):
                    continue
                for key in ("latin", "darija_latin", "text_latin", "arabic", "darija_arabic", "text_arabic"):
                    if turn.get(key):
                        rows.append({"text": turn[key], "label": is_scam, "campaign": sc.get("theme", "vish"),
                                     "lang": "dar_ar" if "arab" in key else "dar_lat", "template_id": "",
                                     "source": "vish_darija", "split": "train"})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    df = pd.concat([synthetic(), real_normals(), uci(), vish_darija()], ignore_index=True)
    df["text"] = df["text"].astype(str).str.strip()
    df = df[df["text"].str.len() > 1]
    # a text that appears in both splits goes to train only (no leakage)
    train_texts = set(df.loc[df["split"] == "train", "text"])
    df = df[~((df["split"] == "test") & df["text"].isin(train_texts))]
    df = df.drop_duplicates(subset=["text", "split"]).sample(frac=1, random_state=SEED).reset_index(drop=True)
    for split in ["train", "test"]:
        part = df[df["split"] == split]
        part.to_csv(os.path.join(OUT, f"{split}.csv"), index=False)
        print(f"{split}: {len(part):,} rows | scam={int(part.label.sum()):,} normal={int((part.label == 0).sum()):,}")
        print(part.groupby(["source", "label"]).size().unstack(fill_value=0).to_string(), "\n")
