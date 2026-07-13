"""Simple HTTP reverse proxy: routes hub-api and TermHive through one port."""
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen
from urllib.error import HTTPError
import json

HUB = "http://127.0.0.1:9800"
HIVE = "http://127.0.0.1:3200"
HUB_PREFIXES = ("/api/", "/health", "/wechat", "/dashboard", "/kanban", "/")


class Proxy(BaseHTTPRequestHandler):
    def do_GET(self):
        self._proxy()

    def do_POST(self):
        self._proxy()

    def do_PUT(self):
        self._proxy()

    def do_DELETE(self):
        self._proxy()

    def _proxy(self):
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len) if content_len > 0 else None

        if self.path.startswith(HUB_PREFIXES):
            target = HUB
        else:
            target = HIVE

        try:
            resp = urlopen(f"{target}{self.path}", data=body)
            self.send_response(resp.status)
            for k, v in resp.headers.items():
                if k.lower() not in ("transfer-encoding", "connection"):
                    self.send_header(k, v)
            self.end_headers()
            self.wfile.write(resp.read())
        except HTTPError as e:
            self.send_response(e.code)
            for k, v in e.headers.items():
                if k.lower() not in ("transfer-encoding", "connection"):
                    self.send_header(k, v)
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            self.send_response(502)
            self.end_headers()
            self.wfile.write(f"Proxy error: {e}".encode())


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 18083), Proxy)
    print("Reverse proxy on :18082 → hub :9800 + termhive :3200")
    server.serve_forever()
