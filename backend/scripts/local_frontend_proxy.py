"""Serve the frontend locally and proxy API calls to the existing backend on port 8000."""
from __future__ import annotations

import base64
import json
import os
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

API_HOST = "127.0.0.1"
API_PORT = 8000
BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
FRONTEND_ROOT = PROJECT_ROOT / "frontend"
if not (FRONTEND_ROOT / "index.html").is_file():
    FRONTEND_ROOT = BACKEND_ROOT / "frontend"
if not (FRONTEND_ROOT / "index.html").is_file():
    FRONTEND_ROOT = BACKEND_ROOT
INDEX_FILE = FRONTEND_ROOT / "index.html"
LOCAL_ENV_FILE = BACKEND_ROOT / ".env"
HOP_BY_HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers", "transfer-encoding", "upgrade", "host"}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self._serve_frontend()
        elif self.path == "/api/auth/config":
            self._serve_local_auth_config()
        else:
            self._proxy()

    def do_HEAD(self):
        if self.path == "/":
            self._serve_frontend(head_only=True)
        else:
            self._proxy()

    def do_POST(self):
        self._proxy()

    def do_PUT(self):
        self._proxy()

    def do_PATCH(self):
        self._proxy()

    def do_DELETE(self):
        self._proxy()

    def do_OPTIONS(self):
        self._proxy()

    def _serve_frontend(self, head_only: bool = False):
        if not INDEX_FILE.is_file():
            self.send_error(404, "Frontend file not found")
            return
        content = INDEX_FILE.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        if not head_only:
            self.wfile.write(content)

    def _serve_local_auth_config(self):
        values = dict(os.environ)
        try:
            for line in LOCAL_ENV_FILE.read_text(encoding="utf-8-sig").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                values.setdefault(key.strip(), value.strip().strip("'\""))
        except OSError:
            pass
        url = values.get("SUPABASE_URL", "").strip().rstrip("/")
        key = values.get("SUPABASE_KEY", "").strip()
        is_service_role = key.startswith("sb_secret_")
        parts = key.split(".")
        if len(parts) > 1:
            try:
                payload = parts[1] + "=" * (-len(parts[1]) % 4)
                is_service_role = is_service_role or json.loads(base64.urlsafe_b64decode(payload)).get("role") == "service_role"
            except (ValueError, UnicodeError, json.JSONDecodeError):
                pass
        if not url or not key or is_service_role:
            self._json_response(503, {"detail": "Set SUPABASE_URL and a Supabase anon/public SUPABASE_KEY in backend/.env."})
            return
        self._json_response(200, {"url": url, "anon_key": key})

    def _json_response(self, status: int, payload: dict):
        content = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _proxy(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        headers = {key: value for key, value in self.headers.items() if key.lower() not in HOP_BY_HOP}
        upstream = HTTPConnection(API_HOST, API_PORT, timeout=30)
        try:
            upstream.request(self.command, self.path, body=body, headers=headers)
            response = upstream.getresponse()
            payload = response.read()
            self.send_response(response.status, response.reason)
            for key, value in response.getheaders():
                if key.lower() not in HOP_BY_HOP:
                    self.send_header(key, value)
            self.end_headers()
            if self.command != "HEAD" and payload:
                self.wfile.write(payload)
        except OSError as exc:
            self.send_error(502, f"Backend on port {API_PORT} is unavailable: {exc}")
        finally:
            upstream.close()


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8001), Handler)
    print("Local Virun frontend: http://127.0.0.1:8001/")
    print("Proxying API requests to http://127.0.0.1:8000/")
    server.serve_forever()
