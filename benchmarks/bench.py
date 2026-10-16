"""
Latency + throughput benchmark - run it ON LinuxONE and put the numbers in your video.

    python3 benchmarks/bench.py            # uses all cores
    python3 benchmarks/bench.py --cores 1

Prints per-message latency (p50/p95/p99) on one core and total throughput on N cores,
plus how many messages per day that is. Pure Python engine: no numpy/sklearn needed.
"""
import argparse
import csv
import json
import multiprocessing as mp
import os
import platform
import statistics
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from engine.core import Engine  # noqa: E402

_eng = None


def _init():
    global _eng
    _eng = Engine(os.path.join(ROOT, "model", "redd_lbal.json"))


def _work(texts):
    for t in texts:
        _eng.analyze(t)
    return len(texts)


def corpus(n=5000):
    texts = []
    for name in ["challenge_set", "blind_set", "blind_set2"]:
        with open(os.path.join(ROOT, "data", f"{name}.csv"), encoding="utf-8") as fh:
            texts += [r["text"] for r in csv.DictReader(fh)]
    p = os.path.join(ROOT, "data", "processed", "test.csv")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as fh:
            texts += [r["text"] for r in csv.DictReader(fh)]
    return (texts * (n // max(1, len(texts)) + 1))[:n]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cores", type=int, default=os.cpu_count())
    ap.add_argument("--n", type=int, default=20000)
    a = ap.parse_args()
    texts = corpus(a.n)
    _init()
    for t in texts[:200]:                       # warm-up
        _eng.analyze(t)
    lat = []
    for t in texts[:3000]:
        t0 = time.perf_counter()
        _eng.analyze(t)
        lat.append((time.perf_counter() - t0) * 1000)
    lat.sort()
    chunks = [texts[i::a.cores] for i in range(a.cores)]
    t0 = time.perf_counter()
    with mp.Pool(a.cores, initializer=_init) as pool:
        done = sum(pool.map(_work, chunks))
    dt = time.perf_counter() - t0
    res = {"machine": platform.machine(), "platform": platform.platform(), "python": platform.python_version(),
           "cores_used": a.cores, "latency_ms_1core": {"p50": round(statistics.median(lat), 3),
                                                       "p95": round(lat[int(.95 * len(lat))], 3),
                                                       "p99": round(lat[int(.99 * len(lat))], 3)},
           "throughput_msgs_per_s": int(done / dt), "msgs_per_day": int(done / dt * 86400)}
    print(json.dumps(res, indent=2))
    print(f"\n{res['machine']}: median {res['latency_ms_1core']['p50']} ms per message; "
          f"{res['throughput_msgs_per_s']:,} messages/second on {a.cores} cores = {res['msgs_per_day']:,} per day.")
    os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
    with open(os.path.join(ROOT, "reports", f"bench_{res['machine']}.json"), "w") as fh:
        json.dump(res, fh, indent=2)
