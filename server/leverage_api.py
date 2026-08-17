"""Local-only API bridge for the Leverage dashboard."""
from __future__ import annotations
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from control_plane.company_core import Project
from control_plane.company_ops import intake_project, create_project_plan, system_snapshot

HOST, PORT = "127.0.0.1", 8765
ALLOWED = {"http://localhost", "http://127.0.0.1", "https://newbiezzzzz.github.io"}


def origin_ok(origin: str | None) -> str | None:
    if not origin:
        return None
    p = urlparse(origin)
    base = f"{p.scheme}://{p.netloc}"
    return origin if base in ALLOWED else None


def body(data: dict) -> bytes:
    return json.dumps(data, indent=2).encode()


class Handler(BaseHTTPRequestHandler):
    server_version = "LeverageLocalAPI/1.0"

    def log_message(self, *_args):
        pass

    def send_json(self, code: int, data: dict) -> None:
        raw = body(data)
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        o = origin_ok(self.headers.get("Origin"))
        if o:
            self.send_header("Access-Control-Allow-Origin", o)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Private-Network", "true")
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self):
        o = origin_ok(self.headers.get("Origin"))
        if not o:
            self.send_json(403, {"ok": False, "error": "origin_not_allowed"})
            return
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", o)
        self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health":
            self.send_json(200, {"ok": True, "service": "Leverage Local API", "money_movement": "protected"})
        elif path == "/api/snapshot":
            self.send_json(200, {"ok": True, "snapshot": system_snapshot()})
        else:
            self.send_json(404, {"ok": False, "error": "not_found"})

    def do_POST(self):
        if not origin_ok(self.headers.get("Origin")):
            self.send_json(403, {"ok": False, "error": "origin_not_allowed"})
            return
        try:
            if urlparse(self.path).path != "/api/projects":
                self.send_json(404, {"ok": False, "error": "not_found"})
                return
            length = int(self.headers.get("Content-Length", "0"))
            if length > 65536:
                raise ValueError("request body too large")
            data = json.loads(self.rfile.read(length) or b"{}")
            project = Project(
                id=str(data.get("project_id", "")).strip(),
                name=str(data.get("name", "")).strip(),
                type=str(data.get("type", "general")).strip() or "general",
                description=str(data.get("goal", "")).strip(),
            )
            if not project.id or not project.name or not project.description:
                raise ValueError("project_id, name and goal are required")
            created = intake_project(project)
            tasks = create_project_plan(created.id)
            self.send_json(201, {"ok": True, "project": created.__dict__, "tasks_created": len(tasks)})
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})


def serve() -> None:
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Leverage Local API: http://{HOST}:{PORT}")
    print("Money movement: PROTECTED")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    serve()
