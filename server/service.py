"""
Redd Lbal service logic (pure Python stdlib) - shared by server/app.py (FastAPI) and
server/stdlib_server.py (zero-dependency fallback for any LinuxONE image).

Privacy by design
  * a message is analysed in memory and forgotten: it is never logged, stored or returned
    to anyone else. The friend's prototype printed every message to the console - removed.
  * the Scam Radar keeps ONLY counters: (hour, scam type, verdict) -> count.
  * published radar numbers carry Laplace noise (differential privacy, epsilon per release)
    and small counts are suppressed, so nobody can learn whether one person checked a message.
"""
import json
import math
import os
import platform
import random
import threading
import time
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys  # noqa: E402

sys.path.insert(0, ROOT)
from engine.core import Engine  # noqa: E402

BUNDLE = os.environ.get("REDD_LBAL_MODEL", os.path.join(ROOT, "model", "redd_lbal.json"))
RADAR_FILE = os.environ.get("REDD_LBAL_RADAR", os.path.join(ROOT, "server", "radar_counts.json"))
EPSILON = float(os.environ.get("REDD_LBAL_EPSILON", "1.0"))   # privacy budget per published snapshot
MIN_COUNT = 3                                                    # suppress tiny (noisy) cells
WINDOW_DAYS = 14


def platform_label():
    m = platform.machine().lower()
    if m == "s390x":
        return "IBM LinuxONE / IBM Z (s390x)"
    return f"{platform.system()} {m}"


class Radar:
    """Anonymous counters with a differentially private read-out and a simple spike detector."""

    def __init__(self, path=RADAR_FILE):
        self.path = path
        self.lock = threading.Lock()
        self.counts = defaultdict(int)          # "YYYY-MM-DDTHH|type|verdict" -> n
        self._cache = (0.0, None)
        if os.path.exists(path):
            try:
                with open(path) as fh:
                    self.counts.update(json.load(fh))
            except (OSError, ValueError):
                pass

    def add(self, verdict, stype, when=None):
        hour = time.strftime("%Y-%m-%dT%H", time.gmtime(when or time.time()))
        key = f"{hour}|{stype or 'none'}|{verdict}"
        with self.lock:
            self.counts[key] += 1
            self._cache = (0.0, None)
            self._save()

    def _save(self):
        cutoff = time.strftime("%Y-%m-%dT%H", time.gmtime(time.time() - WINDOW_DAYS * 86400))
        for k in [k for k in self.counts if k[:13] < cutoff]:
            del self.counts[k]
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w") as fh:
                json.dump(self.counts, fh)
            os.replace(tmp, self.path)
        except OSError:
            pass

    @staticmethod
    def _laplace(scale):
        u = random.random() - 0.5
        return -scale * math.copysign(1.0, u) * math.log(1 - 2 * abs(u))

    def snapshot(self):
        """Noisy totals for the last WINDOW_DAYS + trending scam types. Cached 60 s so repeated
        queries cannot average the noise away."""
        now = time.time()
        with self.lock:
            ts, snap = self._cache
            if snap is not None and now - ts < 60:
                return snap
            cutoff = time.strftime("%Y-%m-%dT%H", time.gmtime(now - WINDOW_DAYS * 86400))
            last24 = time.strftime("%Y-%m-%dT%H", time.gmtime(now - 86400))
            by_type, by_type_24h, verdicts = defaultdict(int), defaultdict(int), defaultdict(int)
            for k, n in self.counts.items():
                hour, typ, verdict = k.split("|")
                if hour < cutoff:
                    continue
                verdicts[verdict] += n
                if verdict != "green" and typ != "none":
                    by_type[typ] += n
                    if hour >= last24:
                        by_type_24h[typ] += n
        scale = 1.0 / EPSILON

        def noisy(x):
            v = int(round(x + self._laplace(scale)))
            return v if v >= MIN_COUNT else 0

        types = {t: noisy(n) for t, n in by_type.items()}
        types = {t: n for t, n in sorted(types.items(), key=lambda kv: -kv[1]) if n > 0}
        trending = []
        for t, n24 in by_type_24h.items():
            prev_daily = (by_type[t] - n24) / max(1, WINDOW_DAYS - 1)
            if n24 >= 5 and n24 > 3 * max(prev_daily, 1):     # 3x its usual daily volume
                trending.append({"type": t, "last_24h": noisy(n24), "usual_per_day": round(prev_daily, 1)})
        snap = {"window_days": WINDOW_DAYS, "epsilon": EPSILON, "min_count": MIN_COUNT,
                "totals": {"checks": noisy(sum(verdicts.values())), "red": noisy(verdicts["red"]),
                           "amber": noisy(verdicts["amber"]), "types": types},
                "trending": trending, "generated_at": int(now),
                "note": "Counts only (hour, scam type, verdict). No message text is stored. Laplace noise added."}
        with self.lock:
            self._cache = (now, snap)
        return snap


class Service:
    def __init__(self, bundle=BUNDLE):
        self.engine = Engine(bundle)
        self.radar = Radar()
        self.platform = platform_label()
        self.started = time.time()
        self.n_checked = 0

    def check(self, text, sender=None, lang="en", count=True):
        text = (text or "")[:5000]
        r = self.engine.analyze(text, sender)
        self.n_checked += 1
        if count:
            self.radar.add(r["verdict"], r["type"])
        r.pop("components", None)
        return {"result": r, "explain": self.engine.explain(r, lang if lang in ("dar", "fr", "ar", "en") else "en"),
                "platform": self.platform}

    def batch(self, messages):
        t0 = time.perf_counter()
        out = []
        for m in messages[:10000]:
            if isinstance(m, dict):
                r = self.engine.analyze(str(m.get("text", ""))[:5000], m.get("sender"))
            else:
                r = self.engine.analyze(str(m)[:5000])
            out.append({"verdict": r["verdict"], "risk": r["risk"], "type": r["type"]})
        dt = time.perf_counter() - t0
        return {"results": out, "n": len(out), "seconds": round(dt, 4),
                "messages_per_second": int(len(out) / dt) if dt > 0 else None, "platform": self.platform}

    def health(self):
        return {"status": "ok", "name": "Redd Lbal", "version": self.engine.b.get("version"), "platform": self.platform,
                "python": platform.python_version(), "uptime_s": int(time.time() - self.started),
                "checked_since_start": self.n_checked, "ml_features": len(self.engine.ml.features),
                "rules": len(self.engine.rules)}


def page_html():
    """The single-file web app, wrapped in a document, told it is served by the API."""
    p = os.path.join(ROOT, "webapp", "dist", "redd-lbal.html")
    with open(p, encoding="utf-8") as fh:
        body = fh.read()
    return ('<!doctype html><html><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            '<script>window.RL_SERVER=true</script>'
            '<style>body{margin:0}[hidden]{display:none!important}</style></head><body>' + body + '</body></html>')
