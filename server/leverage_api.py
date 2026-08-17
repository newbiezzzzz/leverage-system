"""Local Leverage dashboard + Control Plane bridge."""
from __future__ import annotations
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from urllib.parse import urlparse, unquote
import mimetypes

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "dashboard"
sys.path.insert(0, str(ROOT))

from control_plane.company_core import Project
from control_plane.company_ops import intake_project, create_project_plan, system_snapshot

HOST, PORT = "127.0.0.1", 8765
ALLOWED = {"http://localhost", "http://127.0.0.1"}


def body(data: dict) -> bytes:
    return json.dumps(data, indent=2).encode()


def safe_dashboard_path(request_path: str) -> Path | None:
    raw = unquote(urlparse(request_path).path)
    if raw == "/" or raw == "/index.html":
        target = DASHBOARD / "index.html"
    else:
        relative = raw.removeprefix("/")
        target = (DASHBOARD / relative).resolve()
    try:
        target.relative_to(DASHBOARD.resolve())
    except ValueError:
        return None
    return target if target.is_file() else None


class Handler(BaseHTTPRequestHandler):
    server_version = "LeverageLocalAPI/1.1"

    def log_message(self, *_args):
        pass

    def send_json(self, code: int, data: dict) -> None:
        raw = body(data)
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health":
            self.send_json(200, {"ok": True, "service": "Leverage Local API", "dashboard": True, "money_movement": "protected"})
            return
        if path == "/api/snapshot":
            self.send_json(200, {"ok": True, "snapshot": system_snapshot()})
            return
        target = safe_dashboard_path(self.path)
        if target:
            data = target.read_bytes()
            content_type, _ = mimetypes.guess_type(str(target))
            self.send_response(200)
            self.send_header("Content-Type", content_type or "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        self.send_json(404, {"ok": False, "error": "not_found"})

    def do_POST(self):
        if urlparse(self.path).path != "/api/projects":
            self.send_json(404, {"ok": False, "error": "not_found"})
            return
        try:
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
    print(f"Leverage Local Dashboard: http://{HOST}:{PORT}/")
    print("Control Plane: READY")
    print("Money movement: PROTECTED")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    serve()
