"""
HTTP Trigger for Whisper Key
Provides a simple HTTP API to control recording via the StateManager.

Endpoints:
    GET /record   - Start recording
    GET /stop     - Stop recording (transcribe + clipboard)
    GET /toggle   - Toggle recording (start if idle, stop if recording)
    GET /cancel   - Cancel active recording
    GET /command  - Start voice command recording
    GET /status   - Get current state (idle/recording/processing/model_loading)
"""

import json
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

logger = logging.getLogger(__name__)


class _TriggerHandler(BaseHTTPRequestHandler):
    """Handles incoming HTTP requests and dispatches to the StateManager."""

    # Suppress default request logging (we log ourselves)
    def log_message(self, format, *args):
        logger.debug("HTTP %s", format % args)

    # ---- helpers ----------------------------------------------------------

    def _json_response(self, status_code: int, data: dict):
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def _ok(self, message: str, **extra):
        body = {"ok": True, "message": message}
        body.update(extra)
        self._json_response(200, body)

    def _error(self, status_code: int, message: str):
        self._json_response(status_code, {"ok": False, "error": message})

    # ---- routing ----------------------------------------------------------

    def do_GET(self):  # noqa: N802
        path = self.path.split("?")[0].rstrip("/")
        sm = self.server.state_manager  # type: ignore[attr-defined]

        if path == "/record":
            self._handle_record(sm)
        elif path == "/stop":
            self._handle_stop(sm)
        elif path == "/toggle":
            self._handle_toggle(sm)
        elif path == "/cancel":
            self._handle_cancel(sm)
        elif path == "/command":
            self._handle_command(sm)
        elif path == "/status":
            self._handle_status(sm)
        else:
            self._error(404, f"Unknown endpoint: {path}")

    # ---- endpoint handlers ------------------------------------------------

    def _handle_record(self, sm):
        state = sm.get_current_state()
        if state != "idle":
            self._error(409, f"Cannot start recording while {state}")
            return
        sm.start_recording()
        self._ok("Recording started")

    def _handle_stop(self, sm):
        state = sm.get_current_state()
        if state != "recording":
            self._error(409, f"Not recording (current state: {state})")
            return
        sm.stop_recording()
        text = sm.last_transcription or ""
        self._ok("Transcription complete", text=text, action="stop")

    def _handle_toggle(self, sm):
        state = sm.get_current_state()
        if state == "idle":
            sm.start_recording()
            self._ok("Recording started", action="record")
        elif state == "recording":
            sm.stop_recording()
            text = sm.last_transcription or ""
            self._ok("Transcription complete", text=text, action="stop")
        else:
            self._error(409, f"Cannot toggle while {state}")

    def _handle_cancel(self, sm):
        state = sm.get_current_state()
        if state == "recording":
            sm.cancel_active_recording()
            self._ok("Recording cancelled")
        else:
            self._error(409, f"Nothing to cancel (current state: {state})")

    def _handle_command(self, sm):
        state = sm.get_current_state()
        if state != "idle":
            self._error(409, f"Cannot start command recording while {state}")
            return
        sm.start_command_recording()
        self._ok("Command recording started")

    def _handle_status(self, sm):
        state = sm.get_current_state()
        self._ok(state, state=state)


class HttpTrigger:
    """Runs a lightweight HTTP server in a daemon thread to control Whisper Key."""

    def __init__(self, state_manager, host: str = "0.0.0.0", port: int = 5757):
        self.state_manager = state_manager
        self.host = host
        self.port = port
        self._server = None
        self._thread = None

    def start(self):
        self._server = HTTPServer((self.host, self.port), _TriggerHandler)
        # Attach state_manager so the handler can reach it via self.server
        self._server.state_manager = self.state_manager  # type: ignore[attr-defined]

        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="http-trigger",
            daemon=True,
        )
        self._thread.start()
        logger.info("HTTP trigger listening on %s:%d", self.host, self.port)

    def stop(self):
        if self._server:
            self._server.shutdown()
            logger.info("HTTP trigger stopped")
