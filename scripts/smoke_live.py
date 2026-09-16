"""Real local stream: pause, reconnect, network closure and black framebuffer."""
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from tecnomata_iptv.app import Window, configure_appearance

root = Path(__file__).resolve().parents[1]
payload = (root / 'runtime/network.ts').read_bytes()
state = {'requests': 0, 'closed': 0}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass
    def do_GET(self):
        state['requests'] += 1
        self.send_response(200)
        self.send_header('Content-Type', 'video/mp2t')
        self.end_headers()
        try:
            while True:
                for offset in range(0, len(payload), 188 * 32):
                    self.wfile.write(payload[offset:offset + 188 * 32])
                    self.wfile.flush()
                    time.sleep(.02)
        except (BrokenPipeError, ConnectionResetError):
            state['closed'] += 1


server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
server.daemon_threads = True
threading.Thread(target=server.serve_forever, daemon=True).start()
app = QApplication(sys.argv[:1])
configure_appearance(app)
window = Window(demo=True, restore=False)
window.show()
window.show_player()
url = f'http://127.0.0.1:{server.server_port}/live.ts'
checks = {'stage': 0, 'attempts': 0, 'engine': None}


def tick():
    try:
        checks['attempts'] += 1
        assert checks['attempts'] < 180, 'timeout'
        video = window.video
        stage = checks['stage']
        if stage == 0 and video.frames > 5 and video.media_ready:
            checks['engine'] = id(video.engine)
            video.toggle_pause()
            assert video.engine.pause
            checks['stage'] = 1
        elif stage == 1:
            window.live_button.click()
            checks['stage'] = 2
        elif stage == 2 and state['requests'] >= 2 and state['closed'] >= 1 and video.media_ready:
            assert id(video.engine) == checks['engine']
            assert not video.engine.pause
            assert video.engine.playlist_count == 1
            # Stop while paused: it must close the connection and clear the image.
            video.toggle_pause()
            window.stop_playback()
            checks['stage'] = 3
        elif stage == 3 and state['closed'] >= 2 and video.engine.idle_active:
            image = video.grabFramebuffer()
            assert not image.isNull()
            for x, y in ((.25, .25), (.5, .5), (.75, .75)):
                color = image.pixelColor(int(image.width()*x), int(image.height()*y))
                assert max(color.red(), color.green(), color.blue()) == 0
            assert video.engine.playlist_count == 0
            assert video.pending_url is None
            assert not window.audio_tracks.isEnabled()
            video.toggle_pause()
            assert video.engine.idle_active
            print('Live smoke: PASS (new HTTP request, old connection closed, unpaused, stop closes paused stream, black framebuffer, playlist empty)')
            window.close()
            app.quit()
            return
        QTimer.singleShot(100, tick)
    except Exception as exc:
        # Only assertions on synthetic local data; no URLs or engine logs.
        print('Live smoke: FAIL', type(exc).__name__, 'stage', checks['stage'])
        window.close()
        app.exit(1)


def start():
    window.playing_kind = 'live'
    window.live_button.show()
    window.video.play(url)
    tick()


QTimer.singleShot(300, start)
result = app.exec()
server.shutdown()
raise SystemExit(result)
