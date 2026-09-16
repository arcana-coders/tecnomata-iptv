"""Red real local: MPEG-TS/H264/AAC, redirect HTTP y fallo visible 403."""
import json
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from tecnomata_iptv.app import Window

root = Path(__file__).resolve().parents[1]
requests = []


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(root / "runtime"), **kwargs)

    def log_message(self, *args):
        pass

    def do_GET(self):
        agent = self.headers.get("User-Agent", "")
        requests.append({"player_agent": agent.startswith("VLC/"), "test_agent": agent})
        if self.path == "/denied" or not agent.startswith("VLC/"):
            self.send_error(403)
        elif self.path == "/channel":
            self.send_response(302)
            self.send_header("Location", "/network.ts")
            self.end_headers()
        else:
            super().do_GET()


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
app = QApplication(sys.argv[:1])
window = Window(True)
window.show()
base = f"http://127.0.0.1:{server.server_port}"
messages = []
errors = []
window.video.state_changed.connect(messages.append)
window.video.failed.connect(errors.append)
state = {"step": 0, "ticks": 0, "frames": 0}
timer = QTimer()


def check():
    state["ticks"] += 1
    try:
        assert state["ticks"] < 150, "Timeout"
        if state["step"] == 0:
            if window.video.engine:
                window.video.play(base + "/channel")
                state["step"] = 1
        elif state["step"] == 1:
            if window.video.diagnostic["state"] == "playing":
                assert not errors, errors
                assert window.video.engine.video_format == "h264", "No hay decoder H264"
                assert "aac" in window.video.engine.audio_codec.lower(), "No hay decoder AAC"
                image = window.video.grabFramebuffer()
                color = image.pixelColor(image.width() // 2, image.height() // 2)
                if color.green() <= 30 or color.blue() <= 30:
                    return  # Audio can start just before the first video frame.
                state["frames"] = window.video.frames
                window.video.play(base + "/denied")
                state["step"] = 2
        elif errors:
            assert window.video.diagnostic.get("http_status") == 403, "No se capturó HTTP 403"
            assert "403" in errors[-1], "Fallo sin detalle HTTP"
            assert all(request["player_agent"] for request in requests), f"User-Agent incorrecto en servidor local: {requests}"
            print(json.dumps({"result": "PASS", "h264_aac_over_http": True,
                "redirect": True, "http_403_visible": True,
                "player_user_agent": True, "frames": state["frames"]}))
            timer.stop()
            window.close()
            server.shutdown()
            app.exit(0)
    except Exception as exc:
        print(json.dumps({"result": "FAIL", "error": str(exc)}))
        timer.stop()
        window.close()
        server.shutdown()
        app.exit(1)


timer.timeout.connect(check)
timer.start(100)
raise SystemExit(app.exec())
