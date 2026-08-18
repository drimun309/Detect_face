"""Local static frontend + /api proxy. No Docker."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "frontend"
API = "http://127.0.0.1:7030"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        if self.path.startswith("/api/"):
            return self._proxy()
        return super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/"):
            return self._proxy()
        self.send_error(405)

    def do_PUT(self):
        if self.path.startswith("/api/"):
            return self._proxy()
        self.send_error(405)

    def do_DELETE(self):
        if self.path.startswith("/api/"):
            return self._proxy()
        self.send_error(405)

    def do_PATCH(self):
        if self.path.startswith("/api/"):
            return self._proxy()
        self.send_error(405)

    def _proxy(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else None
        req = urllib.request.Request(
            API + self.path,
            data=body,
            method=self.command,
            headers={
                k: v
                for k, v in self.headers.items()
                if k.lower() not in {"host", "content-length", "transfer-encoding", "connection"}
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = resp.read()
                self.send_response(resp.status)
                for k, v in resp.headers.items():
                    if k.lower() not in {"transfer-encoding", "connection", "content-encoding"}:
                        self.send_header(k, v)
                self.end_headers()
                self.wfile.write(data)
        except Exception as exc:
            msg = str(exc).encode("utf-8", "replace")
            self.send_response(502)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", 8081), Handler)
    print("frontend http://127.0.0.1:8081  -> api", API)
    server.serve_forever()
