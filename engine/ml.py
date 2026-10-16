"""Pure-Python scorer for the exported TF-IDF + logistic-regression model (no numpy)."""
import json
import math

from .text import ngram_features


class MLModel:
    def __init__(self, path_or_dict):
        d = path_or_dict
        if isinstance(path_or_dict, str):
            with open(path_or_dict, encoding="utf-8") as fh:
                d = json.load(fh)
        self.features = d["features"]          # feature -> [idf, weight]
        self.intercept = d["intercept"]

    def score(self, tokens):
        """Return (logit, per-token contribution list)."""
        norms = [t["norm"] for t in tokens]
        counts, where = {}, {}
        for f, i in ngram_features(norms):
            if f in self.features:
                counts[f] = counts.get(f, 0) + 1
                where.setdefault(f, []).append(i)
        if not counts:
            return self.intercept, [0.0] * len(tokens)
        vals = {f: (1.0 + math.log(c)) * self.features[f][0] for f, c in counts.items()}
        norm = math.sqrt(sum(v * v for v in vals.values())) or 1.0
        logit = self.intercept
        contrib = [0.0] * len(tokens)
        for f, v in vals.items():
            c = self.features[f][1] * v / norm
            logit += c
            occ = where[f]
            share = c / len(occ)
            for i in occ:
                contrib[i] += share
        return logit, contrib
