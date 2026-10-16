"""
Bundle the web app into ONE self-contained HTML file (engine + model + UI), so it works
offline on a phone, as a published artifact, or served by server/app.py.

    python webapp/build_web.py   ->  webapp/dist/redd-lbal.html
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def summary():
    """Compact evaluation numbers for the 'How it works' table."""
    p = os.path.join(ROOT, "reports", "results.json")
    if not os.path.exists(p):
        return None
    R = json.load(open(p, encoding="utf-8"))
    out = {k: R[k] for k in ["real_moroccan_messages", "unseen_templates", "official_moroccan_sites", "latency_ms"] if k in R}
    out["unseen_templates"] = {k: v for k, v in out["unseen_templates"].items() if not isinstance(v, dict)}
    out["real_moroccan_messages"] = {k: v for k, v in out["real_moroccan_messages"].items() if not isinstance(v, dict)}
    # first-run blind results (recorded before any fix): blind-1 on v0.2, blind-2 on v0.3
    first = {"scam": 0, "scam_flagged": 0, "legit": 0, "legit_red": 0}
    for f in ["blind1_first_run_v0.2.txt", "blind2_first_run_v0.3.txt"]:
        fp = os.path.join(ROOT, "reports", f)
        if not os.path.exists(fp):
            continue
        txt = open(fp, encoding="utf-8").read()
        m1 = re.search(r"SCAMS\s+n=(\d+)\s+red=([\d.]+)\s+amber=([\d.]+)", txt)
        m2 = re.search(r"LEGIT\s+n=(\d+)\s+green=([\d.]+)\s+amber=([\d.]+)\s+red\(false alarm\)=([\d.]+)", txt)
        n, red, amb = int(m1.group(1)), float(m1.group(2)), float(m1.group(3))
        first["scam"] += n
        first["scam_flagged"] += round(n * (red + amb))
        nl, fr = int(m2.group(1)), float(m2.group(4))
        first["legit"] += nl
        first["legit_red"] += round(nl * fr)
    if first["scam"]:
        out["blind_first_run"] = {"scam_flagged": first["scam_flagged"] / first["scam"], "legit_red": first["legit_red"] / first["legit"],
                                  "n": first["scam"] + first["legit"]}
    sets = R.get("sets", {})
    origs = [s["original"]["scam_red"] for s in sets.values() if "original" in s and "scam_red" in s["original"]]
    if origs:
        out["original_scam_caught_range"] = f"{round(min(origs) * 100)}-{round(max(origs) * 100)}%"
    return out


def build(out=os.path.join(ROOT, "webapp", "dist", "redd-lbal.html")):
    html = open(os.path.join(ROOT, "webapp", "app.html"), encoding="utf-8").read()
    engine = open(os.path.join(ROOT, "webapp", "engine.js"), encoding="utf-8").read()
    model = open(os.path.join(ROOT, "model", "redd_lbal.json"), encoding="utf-8").read().replace("</", "<\\/")
    res = json.dumps(summary(), ensure_ascii=False).replace("</", "<\\/")
    html = html.replace("__MODEL_JSON__", model).replace("__RESULTS_JSON__", res).replace("__ENGINE_JS__", engine)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)
    return out


if __name__ == "__main__":
    p = build()
    print(f"wrote {p} ({os.path.getsize(p) / 1e6:.2f} MB)")
