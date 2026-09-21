"""Render OpenGL de libmpv: no crea ventanas ni procesos mpv externos."""
import subprocess
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from .diagnostics import classify_error, failure_message, text_value
from .i18n import t


class VideoWidget(QOpenGLWidget):
    redraw = Signal()
    failed = Signal(str)
    state_changed = Signal(str)
    media_changed = Signal(object)
    clicked = Signal()
    position_changed = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 180)
        self.engine = None
        self.renderer = None
        self.pending_url = None
        self.init_error = None
        self.closed = False
        self.subtitle_scale = 1.0
        self.frames = 0
        self.media_ready = False
        self.media_info = {}
        self.diagnostic = {"state": "idle"}
        self.screensaver_inhibitor = None
        self.poll = QTimer(self)
        self.poll.timeout.connect(self.poll_state)
        self.poll.start(250)
        self.redraw.connect(self.update, Qt.ConnectionType.QueuedConnection)

    def set_screensaver_inhibited(self, inhibited):
        # libmpv en modo render-API (embebido en este widget) no trae ventana propia,
        # así que su inhibición nativa de protector de pantalla no aplica: la hacemos
        # aquí vía logind, independiente del compositor (Hyprland, GNOME, KDE...).
        if inhibited and self.screensaver_inhibitor is None:
            try:
                self.screensaver_inhibitor = subprocess.Popen(
                    ["systemd-inhibit", "--what=idle:sleep", "--who=Tecnomata IPTV",
                     "--why=Reproduciendo contenido", "sleep", "infinity"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except OSError:
                self.screensaver_inhibitor = None
        elif not inhibited and self.screensaver_inhibitor is not None:
            self.screensaver_inhibitor.terminate()
            self.screensaver_inhibitor = None

    def initializeGL(self):
        if self.closed:
            return
        try:
            import locale, ctypes
            try:
                locale.setlocale(locale.LC_NUMERIC, "C")
            except Exception:
                pass
            try:
                ctypes.CDLL(None).setlocale(1, b"C")
            except Exception:
                pass
            import mpv
            self.engine = mpv.MPV(vo="libmpv", config=False, idle=True,
                                  hwdec="no", terminal=False, volume=65,
                                  user_agent="VLC/3.0.21 LibVLC/3.0.21", network_timeout=20,
                                  log_handler=self.engine_log, loglevel="warn",
                                  input_default_bindings=False, input_vo_keyboard=False,
                                  osd_level=0)
            for opt, val in (("osc", "no"), ("ytdl", "no")):
                try:
                    self.engine._set_property(opt, val)
                except Exception:
                    pass
            self.engine.sub_scale = self.subtitle_scale
            self.proc = mpv.MpvGlGetProcAddressFn(
                lambda _ctx, name: int(self.context().getProcAddress(name)))
            self.renderer = mpv.MpvRenderContext(self.engine, "opengl",
                opengl_init_params={"get_proc_address": self.proc})
            self.renderer.update_cb = self.redraw.emit
            self.context().aboutToBeDestroyed.connect(self.dispose)
            @self.engine.event_callback("file-loaded")
            def loaded(_event):
                self.media_ready = True
            self._loaded = loaded
            @self.engine.event_callback("end-file")
            def ended(event):
                reason = text_value(event.as_dict().get("reason"))
                if reason == "error":
                    self.media_ready = False
                    self.diagnostic["state"] = "error"
                    self.set_screensaver_inhibited(False)
                    self.failed.emit(failure_message(self.diagnostic))
                elif reason == "eof":
                    self.diagnostic["state"] = "ended"
                    self.set_screensaver_inhibited(False)
                    self.state_changed.emit("ended")
            self._ended = ended
            if self.pending_url:
                self.play(self.pending_url)
        except Exception as err:
            import traceback
            traceback.print_exc()
            self.init_error = t('error_opengl')
            self.diagnostic = {"state": "error", "failure": "opengl"}
            self.failed.emit(self.init_error)

    def paintGL(self):
        if not self.pending_url:
            # libmpv can retain its last framebuffer after stop; explicitly clear it.
            functions = self.context().functions()
            functions.glClearColor(0, 0, 0, 1)
            functions.glClear(0x00004000)  # GL_COLOR_BUFFER_BIT
            return
        if self.renderer and not self.closed:
            ratio = self.devicePixelRatioF()
            self.renderer.render(flip_y=True, opengl_fbo={
                "fbo": self.defaultFramebufferObject(),
                "w": int(self.width() * ratio), "h": int(self.height() * ratio)})
            self.frames += 1

    def play(self, url):
        self.reset_media()
        self.pending_url = url
        self.diagnostic = {"state": "loading"}
        self.state_changed.emit("connecting")
        if self.init_error:
            self.failed.emit(self.init_error)
        elif self.engine:
            try:
                self.engine.command("loadfile", url, "replace")
                self.engine.pause = False
            except Exception:
                self.diagnostic["state"] = "error"
                self.failed.emit(t('error_open_content'))

    def engine_log(self, prefix, level, message):
        # Log text may include a URL with secrets. Keep only whitelisted codes.
        diagnostic = classify_error(message)
        if diagnostic:
            self.diagnostic.update(diagnostic)

    def poll_state(self):
        if not self.engine or self.closed or self.diagnostic.get("state") not in ("loading", "playing", "paused"):
            return
        self.read_media()
        if not self.media_ready:
            return
        try:
            position = self.engine.time_pos
            duration = self.engine.duration
            self.position_changed.emit({'position': position or 0, 'duration': duration or 0,
                                        'seekable': bool(self.engine.seekable)})
            if position is not None:
                state = "paused" if self.engine.pause else "playing"
                if self.diagnostic["state"] != state:
                    self.diagnostic["state"] = state
                    self.set_screensaver_inhibited(state == "playing")
                    self.state_changed.emit(state)
        except Exception:
            pass

    def reset_media(self):
        self.media_ready = False
        self.media_info = {}
        self.media_changed.emit({})
        self.position_changed.emit({})

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def seek_to(self, seconds):
        if not self.engine or not self.pending_url or not self.media_ready:
            return False
        try:
            duration = self.engine.duration or 0
            if not self.engine.seekable or duration <= 0:
                return False
            self.engine.command('seek', max(0, min(float(seconds), duration)), 'absolute+exact')
            return True
        except Exception:
            self.failed.emit(t('error_seek'))
            return False

    def read_media(self):
        if not self.media_ready:
            return
        try:
            params = self.engine.video_params or {}
            tracks = self.engine.track_list or []
            info = {"width": params.get("w"), "height": params.get("h"),
                    "fps": round(self.engine.container_fps or 0, 2),
                    "codec": text_value(self.engine.video_codec),
                    "audio": [], "sub": [],
                    "aid": self.engine.aid, "sid": self.engine.sid}
            for track in tracks:
                kind = track.get("type")
                if kind in ("audio", "sub") and isinstance(track.get("id"), int):
                    info[kind].append({key: track[key] for key in
                        ("id", "lang", "title", "codec") if key in track})
            if info != self.media_info:
                self.media_info = info
                self.media_changed.emit(info)
        except Exception:
            pass  # A property may temporarily disappear during stream changes.

    def select_track(self, kind, track_id):
        if not self.engine or not self.media_ready:
            return
        if kind not in ("audio", "sub"):
            return
        available = [track["id"] for track in self.media_info.get(kind, [])]
        if track_id not in available and not (kind == "sub" and track_id == "no"):
            return
        try:
            setattr(self.engine, "aid" if kind == "audio" else "sid", track_id)
            if kind == "sub":
                self.engine.sub_visibility = track_id != "no"
            self.read_media()
        except Exception:
            self.failed.emit(t('error_track'))

    def set_subtitle_scale(self, value):
        self.subtitle_scale = max(.5, min(2.5, float(value)))
        if self.engine:
            try:
                self.engine.sub_scale = self.subtitle_scale
            except Exception:
                self.failed.emit(t('error_subtitle_size'))

    def toggle_pause(self):
        if self.engine and self.pending_url:
            self.engine.pause = not self.engine.pause

    def reconnect_current(self):
        url = self.pending_url
        if not url:
            return
        self.stop()
        self.play(url)
        self.state_changed.emit("reconnecting")

    def stop(self):
        self.reset_media()
        self.pending_url = None
        self.diagnostic = {"state": "idle"}
        self.set_screensaver_inhibited(False)
        self.state_changed.emit("stopped")
        if self.engine:
            try:
                self.engine.command("stop")
            except Exception:
                self.failed.emit(t('error_stop'))
        self.update()

    def set_volume(self, value):
        if self.engine:
            self.engine.volume = value

    def dispose(self):
        if self.closed:
            return
        self.closed = True
        self.set_screensaver_inhibited(False)
        self.poll.stop()
        self.makeCurrent()
        if self.renderer:
            self.renderer.update_cb = None
            self.renderer.free()
            self.renderer = None
        self.doneCurrent()
        if self.engine:
            self.engine.terminate()
            self.engine = None
