"""Local web interface (standard library only). Run: python3 -m amsplanner serve"""
from __future__ import annotations
import base64, json, os, tempfile, threading, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from .parsers import parse_file
from .history import FilamentHistory
from .planner import plan
from .model import Job

HTML = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "AMSPlanner.html")


class H(BaseHTTPRequestHandler):
    hist = None

    def _json(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path == "/api/history":
            return self._json(self.hist.quick_select(50))
        with open(HTML, "rb") as f:
            b = f.read()
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])) or b"{}")
        try:
            if self.path == "/api/parse":
                out = []
                for f in data["files"]:
                    suffix = ".gcode.3mf" if f["name"].lower().endswith(".gcode.3mf") else os.path.splitext(f["name"])[1]
                    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as t:
                        t.write(base64.b64decode(f["b64"])); p = t.name
                    for j in parse_file(p):
                        j.name = j.name.replace(os.path.basename(p), f["name"])
                        out.append({"name": j.name, "filaments": sorted(j.filaments), "est_time_s": j.est_time_s,
                                    "source": j.source, "missing": j.missing})
                    os.unlink(p)
                return self._json(out)
            if self.path == "/api/history":
                return self._json({"key": self.hist.record(data["type"].upper(), data["color"].upper(), data.get("label", ""))})
            if self.path == "/api/plan":
                jobs = [Job(j["name"], frozenset(j["filaments"]), j.get("est_time_s")) for j in data["jobs"]]
                for j in jobs:
                    for k in j.filaments:
                        if "?" not in k: self.hist.record(*k.split(":", 1))
                return self._json(plan(jobs, data.get("initial", []), data.get("method", "auto")))
        except Exception as e:  # report to the UI
            return self._json({"error": str(e)}, 400)
        self._json({"error": "unknown endpoint"}, 404)


def run(port: int = 8765, open_browser: bool = True):
    H.hist = FilamentHistory()
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    url = f"http://127.0.0.1:{port}/"
    print("AMS Planner running at", url)
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    srv.serve_forever()
