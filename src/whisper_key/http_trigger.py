import json
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from .state_manager import ListeningMode

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
        elif path == "/mode":
            self._handle_mode_info(sm)
        elif path == "/mode/hotkey":
            self._handle_set_mode(sm, ListeningMode.HOTKEY)
        elif path == "/mode/continuous":
            self._handle_set_mode(sm, ListeningMode.CONTINUOUS)
        elif path == "/mode/wake_word":
            self._handle_set_mode(sm, ListeningMode.WAKE_WORD)
        elif path == "/mode/preview/on":
            self._handle_set_preview(sm, True)
        elif path == "/mode/preview/off":
            self._handle_set_preview(sm, False)
        elif path == "/preview":
            self._handle_preview(sm)
        elif path == "/overlay":
            self._handle_overlay_config(sm)
        elif path == "/overlay/toggle":
            self._handle_overlay_toggle(sm)
        elif path.startswith("/overlay/monitor/"):
            value = path.split("/overlay/monitor/", 1)[1]
            self._handle_overlay_monitor(sm, value)
        elif path.startswith("/overlay/position/"):
            value = path.split("/overlay/position/", 1)[1]
            self._handle_overlay_position(sm, value)
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
        mode_info = sm.get_mode_info()
        self._ok(state, state=state, **mode_info)

    def _handle_mode_info(self, sm):
        mode_info = sm.get_mode_info()
        self._json_response(200, {"ok": True, **mode_info})

    def _handle_set_mode(self, sm, mode: ListeningMode):
        sm.set_listening_mode(mode)
        mode_info = sm.get_mode_info()
        self._json_response(200, {"ok": True, **mode_info})

    def _handle_set_preview(self, sm, enabled: bool):
        sm.set_preview_enabled(enabled)
        mode_info = sm.get_mode_info()
        self._json_response(200, {"ok": True, **mode_info})

    def _handle_preview(self, sm):
        preview = sm.get_last_preview_text()
        self._json_response(200, {"ok": True, **preview})

    def _handle_overlay_config(self, sm):
        config = sm.get_overlay_config()
        try:
            from .platform import monitors
            available = []
            for m in monitors.enumerate_monitors():
                available.append({
                    "index": m.index, "name": m.name,
                    "primary": m.is_primary,
                    "width": m.width, "height": m.height,
                })
            config["monitors_available"] = available
        except Exception:
            config["monitors_available"] = []
        self._json_response(200, {"ok": True, **config})

    def _handle_overlay_toggle(self, sm):
        new_state = not sm.preview_show_overlay
        sm.set_overlay_enabled(new_state)
        sm.system_tray.refresh_menu()
        self._ok(f"Overlay {'enabled' if new_state else 'disabled'}", overlay=new_state)

    def _handle_overlay_monitor(self, sm, value: str):
        VALID_NAMES = {"follow_focus", "cursor", "primary", "all"}
        if value in VALID_NAMES:
            monitor_value = value
        else:
            try:
                monitor_value = int(value)
            except ValueError:
                self._error(400, f"Invalid monitor value: {value}")
                return
        sm.set_overlay_monitor(monitor_value)
        sm.system_tray.refresh_menu()
        self._ok(f"Monitor set to {monitor_value}", monitor=monitor_value)

    def _handle_overlay_position(self, sm, value: str):
        VALID_POSITIONS = {
            "bottom_center", "top_center", "bottom_left", "bottom_right",
            "top_left", "top_right", "center",
        }
        if value not in VALID_POSITIONS:
            self._error(400, f"Invalid position: {value}")
            return
        sm.set_overlay_position(value)
        sm.system_tray.refresh_menu()
        self._ok(f"Position set to {value}", position=value)


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
