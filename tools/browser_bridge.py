"""Local Browser Worker bridge for n8n.

Listens only on 127.0.0.1 and accepts tightly constrained presentation goals.
Financial/account/security actions remain blocked by the Browser Worker itself.
"""
from __future__ import annotations

import json
import os
import subprocess
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

        try:
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
            output = (completed.stdout or "") + "\n" + (completed.stderr or "")
            output = output.strip()
            if completed.returncode != 0:
                self._json(500, {
                    "ok": False,
                    "accepted": True,
                    "completed": True,
                    "return_code": completed.returncode,
                    "goal": goal,
                    "error": output or f"browser worker exited with code {completed.returncode}",
                })
                return

            try:
                result = json.loads(output)
                if not isinstance(result, dict):
                    raise ValueError("worker output was not a JSON object")
            except Exception as exc:
                self._json(500, {
                    "ok": False,
                    "accepted": True,
                    "completed": True,
                    "goal": goal,
                    "error": f"invalid_worker_output: {exc}",
                    "raw_output": output,
                })
                return

            result.update({"accepted": True, "completed": True, "goal": goal})
            self._json(200 if result.get("ok") else 422, result)
        except subprocess.TimeoutExpired:
            self._json(504, {
                "ok": False,
                "accepted": True,
                "completed": False,
                "goal": goal,
                "error": f"browser worker timed out after {TIMEOUT_SECONDS}s",
            })
        except Exception as exc:
            self._json(500, {"ok": False, "error": str(exc), "goal": goal})


if __name__ == "__main__":
    print(f"Leverage Browser Bridge listening on http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
