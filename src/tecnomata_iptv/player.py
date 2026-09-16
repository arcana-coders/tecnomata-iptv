"""Render OpenGL de libmpv: no crea ventanas ni procesos mpv externos."""
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from .diagnostics import classify_error, failure_message, text_value


class VideoWidget(QOpenGLWidget):
    redraw = Signal()
    failed = Signal(str)
    state_changed = Signal(str)
    media_changed = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 180)
        self.engine = None
        self.renderer = None
        self.pending_url = None
        self.init_error = None
        self.closed = False
        self.frames = 0
        self.media_ready = False
        self.media_info = {}
        self.diagnostic = {"state": "idle"}
        self.poll = QTimer(self)
        self.poll.timeout.connect(self.poll_state)
        self.poll.start(250)
        self.redraw.connect(self.update, Qt.ConnectionType.QueuedConnection)

    def initializeGL(self):
        if self.closed:
            return
        try:
            import mpv
            self.engine = mpv.MPV(vo="libmpv", config=False, idle=True,
                                  hwdec="no", terminal=False, volume=65,
                                  ytdl=False,
                                  user_agent="VLC/3.0.21 LibVLC/3.0.21", network_timeout=20,
                                  log_handler=self.engine_log, loglevel="warn",
                                  input_default_bindings=False, input_vo_keyboard=False,
                                  osd_level=0, osc=False)
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
                    self.failed.emit(failure_message(self.diagnostic))
                elif reason == "eof":
                    self.diagnostic["state"] = "ended"
                    self.state_changed.emit("Reproducción terminada")
            self._ended = ended
            if self.pending_url:
                self.play(self.pending_url)
        except Exception:
            self.init_error = "No se pudo iniciar el video integrado. Revisa libmpv y el soporte OpenGL."
            self.diagnostic = {"state": "error", "failure": "opengl"}
            self.failed.emit(self.init_error)

    def paintGL(self):
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
        self.state_changed.emit("Conectando con el video…")
        if self.init_error:
            self.failed.emit(self.init_error)
        elif self.engine:
            try:
                self.engine.command("loadfile", url, "replace")
                self.engine.pause = False
            except Exception:
                self.diagnostic["state"] = "error"
                self.failed.emit("No se pudo abrir el contenido seleccionado.")

    def engine_log(self, prefix, level, message):
        # Log text may include a URL with secrets. Keep only whitelisted codes.
        diagnostic = classify_error(message)
        if diagnostic:
            self.diagnostic.update(diagnostic)

    def poll_state(self):
        if not self.engine or self.closed or self.diagnostic.get("state") not in ("loading", "playing", "paused"):
            return
        self.read_media()
        try:
            position = self.engine.time_pos
            if position is not None:
                state = "paused" if self.engine.pause else "playing"
                if self.diagnostic["state"] != state:
                    self.diagnostic["state"] = state
                    self.state_changed.emit("En pausa" if state == "paused" else "Reproduciendo")
        except Exception:
            pass

    def reset_media(self):
        self.media_ready = False
        self.media_info = {}
        self.media_changed.emit({})

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
            self.read_media()
        except Exception:
            self.failed.emit("No se pudo cambiar la pista. Vuelve a intentar.")

    def toggle_pause(self):
        if self.engine:
            self.engine.pause = not self.engine.pause

    def stop(self):
        self.reset_media()
        self.pending_url = None
        self.diagnostic = {"state": "idle"}
        self.state_changed.emit("Reproducción detenida")
        if self.engine:
            self.engine.command("stop")

    def set_volume(self, value):
        if self.engine:
            self.engine.volume = value

    def dispose(self):
        if self.closed:
            return
        self.closed = True
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
