"""Local Leverage dashboard + Control Plane bridge."""
from __future__ import annotations
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from urllib.parse import urlparse, unquote
import mimetypes
import traceback

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "dashboard"
CONTROL_PLANE = ROOT / "control_plane"
TRACKED_PROJECTS_FILE = CONTROL_PLANE / "projects.json"
PROJECT_TYPES_FILE = CONTROL_PLANE / "project_types.json"
PROJECT_METRICS_FILE = CONTROL_PLANE / "project_metrics.json"
ACQUISITION_QUEUE_FILE = CONTROL_PLANE / "acquisition_queue.json"
PROSPECTS_FILE = CONTROL_PLANE / "prospects.json"
sys.path.insert(0, str(ROOT))

from control_plane.company_core import Project
from control_plane.company_ops import intake_project, create_project_plan, system_snapshot
from control_plane.gates import project_gate_report
from control_plane.health import company_health
from control_plane.readiness import company_os_readiness
from control_plane.delivery_gateway import create_order, get_order, list_orders
from control_plane.runtime_state import ensure_runtime_state, state_path
from control_plane.buyer_pipeline_store import ensure_prospect, get_pipeline, list_pipelines, transition_pipeline

HOST, PORT = "127.0.0.1", 8765
API_VERSION = "2.1"


def body(data: dict) -> bytes:
    return json.dumps(data, indent=2, default=str).encode()


def safe_dashboard_path(request_path: str) -> Path | None:
    raw = unquote(urlparse(request_path).path)
    if raw in {"/", "/index.html"}:
        target = DASHBOARD / "command.html"
    else:
        target = (DASHBOARD / raw.removeprefix("/")).resolve()
    try:
        target.relative_to(DASHBOARD.resolve())
    except ValueError:
        return None
    return target if target.is_file() else None


def _read_project_file(path: Path) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        records = data.get("projects", [])
        return records if isinstance(records, list) else []
    except (OSError, json.JSONDecodeError, AttributeError):
        return []


def _read_json_file(path: Path, fallback: dict) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else fallback
    except (OSError, json.JSONDecodeError):
        return fallback


def read_project_records() -> list[dict]:
    """Return authoritative raw project records, preserving extended metadata."""
    ensure_runtime_state()
    runtime_records = _read_project_file(state_path("projects.json"))
    if runtime_records:
        return runtime_records
    return _read_project_file(TRACKED_PROJECTS_FILE)


def read_acquisition_queue() -> dict:
    """Return a stable, backward-compatible acquisition queue shape."""
    queue = _read_json_file(
        ACQUISITION_QUEUE_FILE,
        {"version": 0, "items": [], "prospect_validation": [], "tracking": {}},
    )
    if not isinstance(queue.get("items"), list):
        queue["items"] = []
    if not isinstance(queue.get("prospect_validation"), list):
        queue["prospect_validation"] = []
    if not isinstance(queue.get("tracking"), dict):
        queue["tracking"] = {}
    queue.setdefault("version", 0)
    queue["schema_version"] = 3
    return queue


def ensure_buyer_pipeline_candidates() -> int:
    """Materialize discovered prospects into the persistent buyer funnel without advancing them."""
    prospects = _read_json_file(PROSPECTS_FILE, {}).get("prospects", [])
    created = 0
    if not isinstance(prospects, list):
        return 0
    for prospect in prospects:
        prospect_id = str(prospect.get("id", "")).strip()
        if prospect_id and prospect.get("public_contact_available"):
            before = {item.get("prospect_id") for item in list_pipelines()}
            ensure_prospect(prospect_id)
            if prospect_id not in before:
                created += 1
    return created


class Handler(BaseHTTPRequestHandler):
    server_version = f"LeverageLocalAPI/{API_VERSION}"

    def log_message(self, *_args):
        pass

    def send_json(self, code: int, data: dict) -> None:
        raw = body(data)
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        path = urlparse(self.path).path
        try:
            if path == "/api/health":
                self.send_json(200, {"ok": True, "service": "Leverage Local API", "dashboard": True, "money_movement": "protected", "api_version": API_VERSION})
                return
            if path == "/api/readiness":
                result = company_os_readiness()
                self.send_json(200 if result["ready"] else 503, {"ok": result["ready"], "readiness": result})
                return
            if path == "/api/snapshot":
                self.send_json(200, {"ok": True, "snapshot": system_snapshot()})
                return
            if path == "/api/company-health":
                self.send_json(200, {"ok": True, "health": company_health()})
                return
            if path == "/api/projects":
                self.send_json(200, {"ok": True, "api_version": API_VERSION, "projects": read_project_records()})
                return
            if path == "/api/project-types":
                self.send_json(200, {"ok": True, "types": _read_json_file(PROJECT_TYPES_FILE, {"types": {}})})
                return
            if path == "/api/project-metrics":
                self.send_json(200, {"ok": True, "metrics": _read_json_file(PROJECT_METRICS_FILE, {"projects": {}})})
                return
            if path == "/api/acquisition-queue":
                self.send_json(200, {"ok": True, "queue": read_acquisition_queue()})
                return
            if path == "/api/buyer-pipeline":
                ensure_buyer_pipeline_candidates()
                self.send_json(200, {"ok": True, "pipelines": list_pipelines()})
                return
            if path.startswith("/api/buyer-pipeline/"):
                prospect_id = unquote(path[len("/api/buyer-pipeline/"):]).strip("/")
                self.send_json(200, {"ok": True, "pipeline": get_pipeline(prospect_id)})
                return
            if path == "/api/customer-orders":
                self.send_json(200, {"ok": True, "orders": list_orders()})
                return
            if path.startswith("/api/customer-orders/"):
                order_id = unquote(path[len("/api/customer-orders/"):]).strip("/")
                try:
                    self.send_json(200, {"ok": True, "order": get_order(order_id)})
                except KeyError as exc:
                    self.send_json(404, {"ok": False, "error": str(exc)})
                return
            if path.startswith("/api/projects/") and path.endswith("/gates"):
                project_id = unquote(path[len("/api/projects/"):-len("/gates")]).strip("/")
                try:
                    self.send_json(200, {"ok": True, "report": project_gate_report(project_id)})
                except KeyError as exc:
                    self.send_json(404, {"ok": False, "error": str(exc)})
                except ValueError as exc:
                    self.send_json(400, {"ok": False, "error": str(exc)})
                return
            target = safe_dashboard_path(self.path)
            if target:
                data = target.read_bytes()
                content_type, _ = mimetypes.guess_type(str(target))
                self.send_response(200)
                self.send_header("Content-Type", content_type or "application/octet-stream")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(data)
                return
            self.send_json(404, {"ok": False, "error": "not_found"})
        except Exception as exc:
            traceback.print_exc()
            try:
                self.send_json(500, {"ok": False, "error": type(exc).__name__, "message": str(exc), "api_version": API_VERSION})
            except Exception:
                pass

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 65536:
                raise ValueError("request body too large")
            data = json.loads(self.rfile.read(length) or b"{}")

            if path == "/api/projects":
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
                self.send_json(201, {"ok": True, "project": created.__dict__, "tasks_created": len(tasks), "api_version": API_VERSION})
                return

            if path.startswith("/api/buyer-pipeline/"):
                prospect_id = unquote(path[len("/api/buyer-pipeline/"):]).strip("/")
                target = str(data.get("target", "")).strip()
                if not target:
                    raise ValueError("target is required")
                result = transition_pipeline(
                    prospect_id,
                    target,
                    approvals=[str(x) for x in (data.get("approvals") or [])],
                    evidence=[str(x) for x in (data.get("evidence") or [])],
                )
                self.send_json(200, {"ok": True, "pipeline": result, "api_version": API_VERSION})
                return

            if path == "/api/customer-orders":
                order = create_order(
                    customer_ref=str(data.get("customer_ref", "")),
                    service=str(data.get("service", "")),
                    project_id=str(data.get("project_id", "")),
                    input_manifest=data.get("input_manifest") or [],
                )
                self.send_json(201, {"ok": True, "order": order, "api_version": API_VERSION})
                return

            self.send_json(404, {"ok": False, "error": "not_found", "api_version": API_VERSION})
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            self.send_json(400, {"ok": False, "error": str(exc), "api_version": API_VERSION})
        except Exception as exc:
            traceback.print_exc()
            try:
                self.send_json(500, {"ok": False, "error": type(exc).__name__, "message": str(exc), "api_version": API_VERSION})
            except Exception:
                pass


class SingleInstanceServer(ThreadingHTTPServer):
    allow_reuse_address = True
    allow_reuse_port = False

    def server_bind(self):
        try:
            super().server_bind()
        except OSError as exc:
            raise RuntimeError(f"Leverage API port {PORT} is already in use. Stop the existing LeverageLocalAPI process before starting another instance.") from exc


def serve() -> None:
    httpd = SingleInstanceServer((HOST, PORT), Handler)
    print(f"Leverage Local Dashboard: http://{HOST}:{PORT}/")
    print(f"Control Plane: READY (API {API_VERSION})")
    print("Money movement: PROTECTED")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    serve()
