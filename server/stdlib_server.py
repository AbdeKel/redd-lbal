"""
Zero-dependency Redd Lbal server (Python 3.8+ standard library only).
Same endpoints as server/app.py - use it if `pip install fastapi` is a problem on s390x.

    python3 server/stdlib_server.py --port 8000
"""
import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server.service import Service, page_html  # noqa: E402

svc = Service()
PAGE = None


class Handler(BaseHTTPRequestHandler):
    server_version = "ReddLbal/0.4"

    def log_message(self, fmt, *args):        # never log request bodies (= messages)
        sys.stderr.write("%s %s\n" % (self.command, self.path.split("?")[0]))

    def _send(self, code, payload, ctype="application/json; charset=utf-8"):
        data = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        global PAGE
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            PAGE = PAGE or page_html().encode("utf-8")
            return self._send(200, PAGE, "text/html; charset=utf-8")
        if path == "/api/health":
            return self._send(200, svc.health())
        if path == "/api/radar":
            return self._send(200, svc.radar.snapshot())
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        path = self.path.split("?")[0]
        n = int(self.headers.get("Content-Length") or 0)
        if n > 5_000_000:
            return self._send(413, {"error": "request too large"})
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return self._send(400, {"error": "body must be JSON"})
        if path == "/api/check":
            if not isinstance(body.get("text"), str):
                return self._send(422, {"error": "field 'text' (string) is required"})
            return self._send(200, svc.check(body["text"], body.get("sender"), body.get("lang", "en"), body.get("count", True)))
        if path == "/analyze":
            text = (body.get("message") or "").strip()
            link = (body.get("lien") or "").strip()
            if link and link not in text:
                text = f"{text} {link}".strip() if text else link
            return self._send(200, svc.check(text, body.get("sender"), body.get("lang", "fr"), count=True))
        if path == "/api/batch":
            msgs = body.get("messages")
            if not isinstance(msgs, list):
                return self._send(422, {"error": "field 'messages' (list) is required"})
            return self._send(200, svc.batch(msgs))
        return self._send(404, {"error": "not found"})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8000)
    a = ap.parse_args()
    print(f"Redd Lbal on http://{a.host}:{a.port}  ({svc.platform})")
    ThreadingHTTPServer((a.host, a.port), Handler).serve_forever()
