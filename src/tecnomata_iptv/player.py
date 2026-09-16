"""Render OpenGL de libmpv: no crea ventanas ni procesos mpv externos."""
from PySide6.QtCore import Signal, Qt
from PySide6.QtOpenGLWidgets import QOpenGLWidget


class VideoWidget(QOpenGLWidget):
    redraw = Signal()
    failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 180)
        self.engine = None
        self.renderer = None
        self.pending_url = None
        self.init_error = None
        self.closed = False
        self.frames = 0
        self.redraw.connect(self.update, Qt.ConnectionType.QueuedConnection)

    def initializeGL(self):
        if self.closed:
            return
        try:
            import mpv
            self.engine = mpv.MPV(vo="libmpv", config=False, idle=True,
                                  hwdec="auto-safe", terminal=False, volume=65,
                                  input_default_bindings=False, input_vo_keyboard=False)
            self.proc = mpv.MpvGlGetProcAddressFn(
                lambda _ctx, name: int(self.context().getProcAddress(name)))
            self.renderer = mpv.MpvRenderContext(self.engine, "opengl",
                opengl_init_params={"get_proc_address": self.proc})
            self.renderer.update_cb = self.redraw.emit
            self.context().aboutToBeDestroyed.connect(self.dispose)
            @self.engine.event_callback("end-file")
            def ended(event):
                if event.as_dict().get("reason") == "error":
                    self.failed.emit("No se pudo reproducir este contenido. Revisa la conexión o prueba otro canal.")
            self._ended = ended
            if self.pending_url:
                self.play(self.pending_url)
        except Exception:
            self.init_error = "No se pudo iniciar el video integrado. Revisa libmpv y el soporte OpenGL."
            self.failed.emit(self.init_error)

    def paintGL(self):
        if self.renderer and not self.closed:
            ratio = self.devicePixelRatioF()
            self.renderer.render(flip_y=True, opengl_fbo={
                "fbo": self.defaultFramebufferObject(),
                "w": int(self.width() * ratio), "h": int(self.height() * ratio)})
            self.frames += 1

    def play(self, url):
        self.pending_url = url
        if self.init_error:
            self.failed.emit(self.init_error)
        elif self.engine:
            try:
                self.engine.command("loadfile", url, "replace")
                self.engine.pause = False
            except Exception:
                self.failed.emit("No se pudo abrir el contenido seleccionado.")

    def toggle_pause(self):
        if self.engine:
            self.engine.pause = not self.engine.pause

    def stop(self):
        self.pending_url = None
        if self.engine:
            self.engine.command("stop")

    def set_volume(self, value):
        if self.engine:
            self.engine.volume = value

    def dispose(self):
        if self.closed:
            return
        self.closed = True
        self.makeCurrent()
        if self.renderer:
            self.renderer.update_cb = None
            self.renderer.free()
            self.renderer = None
        self.doneCurrent()
        if self.engine:
            self.engine.terminate()
            self.engine = None
