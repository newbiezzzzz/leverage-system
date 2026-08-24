"""Local Browser Worker bridge for n8n.

Listens only on 127.0.0.1 and accepts tightly constrained presentation goals.
Financial/account/security actions remain blocked by the Browser Worker itself.
"""
from __future__ import annotations

import json
import os
import subprocess
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOST = "127.0.0.1"
PORT = int(os.environ.get("LEVERAGE_BROWSER_BRIDGE_PORT", "8787"))
ALLOWED_PREFIXES = (
    "Optimize P-001 Gumroad listing",
    "Optimize Fabrication Shop Profit & Quote System marketplace listing",
)
RUNNER = ROOT / "tools" / "run-browser-worker.cmd"
TIMEOUT_SECONDS = int(os.environ.get("LEVERAGE_BROWSER_BRIDGE_TIMEOUT", "300"))
JOBS: dict[str, dict] = {}
LOCK = threading.Lock()


def _run_job(job_id: str, goal: str) -> None:
    try:
        with LOCK:
            JOBS[job_id]["status"] = "running"
        env = os.environ.copy()
        completed = subprocess.run(
            [str(RUNNER), goal],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT_SECONDS,
            shell=False,
        )
        output = ((completed.stdout or "") + "\n" + (completed.stderr or "")).strip()
        if completed.returncode != 0:
            result = {
                "ok": False,
                "accepted": True,
                "completed": True,
                "return_code": completed.returncode,
                "goal": goal,
                "error": output or f"browser worker exited with code {completed.returncode}",
            }
        else:
            try:
                result = json.loads(output)
                if not isinstance(result, dict):
                    raise ValueError("worker output was not a JSON object")
                result.update({"accepted": True, "completed": True, "goal": goal})
            except Exception as exc:
                result = {
                    "ok": False,
                    "accepted": True,
                    "completed": True,
                    "goal": goal,
                    "error": f"invalid_worker_output: {exc}",
                    "raw_output": output,
                }
        with LOCK:
            JOBS[job_id].update(result)
            JOBS[job_id]["status"] = "completed"
    except subprocess.TimeoutExpired:
        with LOCK:
            JOBS[job_id].update({
                "ok": False,
                "accepted": True,
                "completed": True,
                "goal": goal,
                "error": f"browser worker timed out after {TIMEOUT_SECONDS}s",
                "status": "completed",
            })
    except Exception as exc:
        with LOCK:
            JOBS[job_id].update({
                "ok": False,
                "accepted": True,
                "completed": True,
                "goal": goal,
                "error": str(exc),
                "status": "completed",
            })


class Handler(BaseHTTPRequestHandler):
    def _json(self, code: int, payload: dict) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, fmt: str, *args) -> None:
        print(fmt % args)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json(200, {"ok": True, "service": "Leverage Browser Bridge", "browser_worker": True})
            return
        if self.path.startswith("/status/"):
            job_id = self.path.split("/status/", 1)[1].strip()
            with LOCK:
                job = JOBS.get(job_id)
                if job is None:
                    self._json(404, {"ok": False, "error": "job_not_found", "job_id": job_id})
                    return
                payload = dict(job)
            code = 200 if payload.get("status") != "completed" else (200 if payload.get("ok") else 422)
            self._json(code, payload)
            return
        self._json(404, {"ok": False, "error": "not_found"})

    def do_POST(self) -> None:
        if self.path != "/run":
            self._json(404, {"ok": False, "error": "not_found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
            goal = str(body.get("goal", "")).strip()
        except Exception as exc:
            self._json(400, {"ok": False, "error": f"invalid_json: {exc}"})
            return
        if not goal or not any(goal.startswith(prefix) for prefix in ALLOWED_PREFIXES):
            self._json(403, {"ok": False, "error": "goal_not_allowed", "allowed_prefixes": ALLOWED_PREFIXES})
            return
        if not RUNNER.exists():
            self._json(500, {"ok": False, "error": "browser_runner_missing", "path": str(RUNNER)})
            return
        job_id = uuid.uuid4().hex
        with LOCK:
            JOBS[job_id] = {
                "ok": True,
                "accepted": True,
                "completed": False,
                "status": "queued",
                "job_id": job_id,
                "goal": goal,
            }
        threading.Thread(target=_run_job, args=(job_id, goal), daemon=True).start()
        self._json(202, dict(JOBS[job_id]))


if __name__ == "__main__":
    print(f"Leverage Browser Bridge listening on http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
