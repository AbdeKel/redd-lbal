"""Build model/redd_lbal.json = knowledge base + ML weights + fusion parameters.
Run after editing engine/knowledge.py or retraining:   python -m engine.export"""
import json
import os

from . import knowledge as K

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUSION_PATH = os.path.join(ROOT, "model", "fusion.json")
DEFAULT_FUSION = {"a": 0.6, "b": -1.0, "floor_critical": 0.93, "cap_no_harm": 0.39, "t_amber": 0.40, "t_red": 0.75, "ml_alone": 0.97, "ml_alone_floor": 0.5}


def knowledge_dict():
    return {k: getattr(K, k) for k in ["CONCEPTS", "BRANDS", "REPUTABLE", "SHORTENERS", "FREEHOST", "CHAT_HOSTS",
                                       "SUS_TLDS", "MULTI_SUFFIXES", "OFFICIAL_SUFFIXES", "SOFT_HARM", "REDUNDANT", "MAX_REASONS", "RULES", "TYPES", "LANGS", "TEXT"]}


def build(ml_path=os.path.join(ROOT, "model", "ml.json"), out=os.path.join(ROOT, "model", "redd_lbal.json"), fusion=None):
    with open(ml_path, encoding="utf-8") as fh:
        ml = json.load(fh)
    if fusion is None:
        fusion = DEFAULT_FUSION
        if os.path.exists(FUSION_PATH):
            with open(FUSION_PATH) as fh:
                fusion = {**DEFAULT_FUSION, **json.load(fh)}
    bundle = {"name": "Redd Lbal", "version": "0.4.0", "fusion": fusion, "knowledge": knowledge_dict(), "ml": ml}
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(bundle, fh, ensure_ascii=False, separators=(",", ":"))
    return out


if __name__ == "__main__":
    p = build()
    print(f"wrote {p} ({os.path.getsize(p) / 1e6:.2f} MB)")
