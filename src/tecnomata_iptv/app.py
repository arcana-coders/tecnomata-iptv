import argparse
import sys
import json
import os
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Qt, QTimer
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QLineEdit, QComboBox, QListWidget,
    QListWidgetItem, QSplitter, QSlider, QDialog, QFormLayout, QDialogButtonBox)

from .xtream import Account, XtreamClient, ServiceError
from .player import VideoWidget


class Signals(QObject):
    done = Signal(object)
    error = Signal(str)


class Job(QRunnable):
    def __init__(self, function):
        super().__init__()
        self.function = function
        self.signals = Signals()

    def run(self):
        try:
            self.signals.done.emit(self.function())
        except ServiceError as exc:
            self.signals.error.emit(str(exc))
        except Exception:
            # Never expose exception text: HTTP URLs contain account secrets.
            self.signals.error.emit("No se pudo completar la operación. Revisa la conexión y vuelve a intentar.")


class Login(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Conectar mi servicio")
        self.setMinimumWidth(440)
        form = QFormLayout(self)
        form.addRow(QLabel("Tus datos sólo se conservan durante esta sesión."))
        self.server = QLineEdit()
        self.server.setPlaceholderText("http://servidor:puerto")
        self.user = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        for label, widget in [("Servidor", self.server), ("Usuario", self.user), ("Contraseña", self.password)]:
            form.addRow(label, widget)
        self.error = QLabel()
        self.error.setWordWrap(True)
        form.addRow(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Conectar")
        buttons.accepted.connect(self.validate)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def validate(self):
        try:
            self.account = Account(self.server.text(), self.user.text(), self.password.text())
            self.accept()
        except (ServiceError, ValueError) as exc:
            self.error.setText(str(exc) if isinstance(exc, ServiceError) else "Servidor inválido.")


class Window(QMainWindow):
    def __init__(self, demo=False, demo_files=()):
        super().__init__()
        self.setWindowTitle("Tecnomata IPTV")
        self.setObjectName("tecnomata-iptv")
        self.resize(1200, 760)
        self.client = None
        self.demo = demo
        self.demo_files = list(demo_files)
        self.kind = "live"
        self.rows = []
        self.in_episodes = False
        self.jobs = set()
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(24, 22, 24, 22)
        top = QHBoxLayout()
        title = QLabel("TECNOMATA  /  IPTV")
        title.setObjectName("brand")
        top.addWidget(title)
        top.addStretch()
        self.connect_button = QPushButton("Conectar mi servicio")
        self.connect_button.clicked.connect(self.login)
        top.addWidget(self.connect_button)
        layout.addLayout(top)
        self.navigation = QWidget()
        nav = QHBoxLayout(self.navigation)
        nav.setContentsMargins(0, 12, 0, 12)
        self.tabs = {}
        for kind, name in [("live", "TV en vivo"), ("vod", "Películas"), ("series", "Series")]:
            button = QPushButton(name)
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, kind=kind: self.section(kind))
            self.tabs[kind] = button
            nav.addWidget(button)
        layout.addWidget(self.navigation)
        filters = QHBoxLayout()
        self.category = QComboBox()
        self.category.addItem("Todas las categorías", None)
        self.category.currentIndexChanged.connect(self.load_catalog)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar en esta sección…")
        self.search.textChanged.connect(self.filter_rows)
        self.back = QPushButton("Volver a series")
        self.back.clicked.connect(lambda: self.section("series"))
        self.back.hide()
        filters.addWidget(self.category, 1)
        filters.addWidget(self.search, 2)
        filters.addWidget(self.back)
        layout.addLayout(filters)
        self.splitter = QSplitter()
        self.items = QListWidget()
        self.items.itemActivated.connect(self.activate)
        self.splitter.addWidget(self.items)
        right = QWidget()
        video_layout = QVBoxLayout(right)
        video_layout.setContentsMargins(12, 0, 0, 0)
        self.now = QLabel("Selecciona un canal, película o episodio")
        self.now.setWordWrap(True)
        video_layout.addWidget(self.now)
        self.video = VideoWidget()
        self.video.failed.connect(self.show_error)
        self.video.state_changed.connect(lambda message: self.status.setText(message))
        video_layout.addWidget(self.video, 1)
        controls = QHBoxLayout()
        for name, function in [("Pausa / seguir", self.video.toggle_pause),
                               ("Detener", self.video.stop), ("Pantalla completa", self.fullscreen)]:
            button = QPushButton(name)
            button.clicked.connect(function)
            controls.addWidget(button)
        volume = QSlider(Qt.Orientation.Horizontal)
        volume.setRange(0, 100)
        volume.setValue(65)
        volume.setMaximumWidth(120)
        volume.valueChanged.connect(self.video.set_volume)
        controls.addWidget(QLabel("Volumen"))
        controls.addWidget(volume)
        video_layout.addLayout(controls)
        self.splitter.addWidget(right)
        self.splitter.setSizes([350, 800])
        layout.addWidget(self.splitter, 1)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.escape = QShortcut(QKeySequence("Escape"), self)
        self.escape.activated.connect(self.exit_fullscreen)
        self.fkey = QShortcut(QKeySequence("F"), self)
        self.fkey.activated.connect(self.fullscreen)
        self.diagnostic_timer = QTimer(self)
        self.diagnostic_timer.timeout.connect(self.save_diagnostic)
        self.diagnostic_timer.start(1000)
        self.section("live")

    def busy(self, value):
        for widget in (self.connect_button, self.navigation, self.category, self.items, self.back):
            widget.setEnabled(not value)

    def submit(self, function, callback):
        self.busy(True)
        self.status.setText("Cargando…")
        job = Job(function)
        self.jobs.add(job)
        def finish(result=None, error=None):
            self.jobs.discard(job)
            self.busy(False)
            if error:
                self.show_error(error)
            else:
                self.status.setText("")
                callback(result)
        job.signals.done.connect(lambda result: finish(result))
        job.signals.error.connect(lambda message: finish(error=message))
        self.pool.start(job)

    def show_error(self, message):
        self.status.setText(message)

    def save_diagnostic(self):
        # Strictly whitelisted engine state: no account, URLs, names or raw logs.
        path = Path(__file__).resolve().parents[2] / "runtime/playback-status.json"
        data = {key: value for key, value in self.video.diagnostic.items()
                if key in ("state", "failure", "http_status")}
        data.update({"engine_initialized": self.video.engine is not None,
                     "renderer_initialized": self.video.renderer is not None,
                     "closed": self.video.closed, "frames": self.video.frames})
        try:
            path.parent.mkdir(exist_ok=True)
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as output:
                json.dump(data, output)
        except OSError:
            pass

    def login(self):
        dialog = Login(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        client = XtreamClient(dialog.account)
        dialog.password.clear()
        dialog.deleteLater()
        def connect():
            try:
                client.authenticate()
                return client
            except Exception:
                client.close()
                raise
        def connected(result):
            self.video.stop()
            if self.client:
                self.client.close()
            self.client = result
            self.demo = False
            self.connect_button.setText("Cambiar servicio")
            self.section(self.kind)
        self.submit(connect, connected)

    def section(self, kind):
        self.kind = kind
        self.in_episodes = False
        self.back.hide()
        self.search.clear()
        for key, button in self.tabs.items():
            button.setChecked(key == kind)
        self.category.blockSignals(True)
        self.category.clear()
        self.category.addItem("Todas las categorías", None)
        self.category.blockSignals(False)
        self.rows = []
        self.filter_rows()
        if self.demo:
            labels = {"live": ["Canal de prueba A", "Canal de prueba B"],
                      "vod": ["Película de prueba"], "series": ["Serie de prueba"]}
            self.rows = [{"name": name, "stream_id": index + 1,
                          "series_id": index + 1} for index, name in enumerate(labels[kind])]
            self.filter_rows()
            self.status.setText("Demostración · catálogo ficticio. Conecta tu servicio para ver tu contenido.")
        elif self.client:
            def loaded(categories):
                self.category.blockSignals(True)
                for row in categories:
                    self.category.addItem(str(row.get("category_name", "Sin nombre")), row.get("category_id"))
                self.category.blockSignals(False)
                self.load_catalog()
            self.submit(lambda: self.client.categories(kind), loaded)
        else:
            self.status.setText("Conecta tu servicio para cargar TV en vivo, películas y series. Doble clic para reproducir.")

    def load_catalog(self):
        if not self.client or self.in_episodes:
            return
        category = self.category.currentData()
        self.submit(lambda: self.client.catalog(self.kind, category), self.set_rows)

    def set_rows(self, rows):
        self.rows = rows
        self.filter_rows()
        self.status.setText(f"{len(rows)} elementos · doble clic o Enter para abrir")

    def filter_rows(self):
        query = self.search.text().casefold().strip()
        self.items.clear()
        for row in self.rows:
            name = str(row.get("name", "Sin nombre"))
            if query in name.casefold():
                item = QListWidgetItem(name)
                item.setData(Qt.ItemDataRole.UserRole, row)
                self.items.addItem(item)

    def activate(self, item):
        row = item.data(Qt.ItemDataRole.UserRole)
        if self.kind == "series" and not self.in_episodes:
            def loaded(episodes):
                self.in_episodes = True
                self.back.show()
                self.search.clear()
                self.set_rows(episodes)
            if self.demo:
                loaded([{"name": "T1 · E1 · Episodio de prueba", "stream_id": 1}])
            else:
                self.submit(lambda: self.client.episodes(row.get("series_id")), loaded)
            return
        if self.demo:
            index = int(row.get("stream_id", 1)) - 1
            if not self.demo_files:
                self.status.setText("Este catálogo es ficticio. Usa --demo-file VIDEO para probar reproducción local.")
                return
            url = str(Path(self.demo_files[index % len(self.demo_files)]).resolve())
        else:
            try:
                url = self.client.stream_url(self.kind, row.get("stream_id"), row.get("container_extension"))
            except ServiceError as exc:
                self.show_error(str(exc))
                return
        self.now.setText(str(row.get("name", "Reproduciendo")))
        self.video.play(url)

    def fullscreen(self):
        if self.isFullScreen():
            self.exit_fullscreen()
        else:
            self.showFullScreen()

    def exit_fullscreen(self):
        self.showNormal()

    def closeEvent(self, event):
        if self.jobs:
            self.status.setText("Espera a que termine la consulta antes de cerrar (máximo 20 segundos por solicitud).")
            event.ignore()
            return
        self.video.dispose()
        if self.client:
            self.client.close()
        event.accept()


STYLE = """
QWidget { background: #101827; color: #e5eaf3; font-size: 14px; }
QLabel#brand { color: #72dac7; font-size: 22px; font-weight: bold; }
QPushButton { background: #223149; border: 1px solid #34465e; border-radius: 8px; padding: 12px 18px; }
QPushButton:hover { background: #304663; }
QPushButton:checked { background: #17685e; border-color: #72dac7; }
QPushButton:disabled { color: #7b879b; }
QLineEdit, QComboBox { background: #182438; border: 1px solid #34465e; border-radius: 7px; padding: 10px; }
QListWidget { background: #182438; border: 1px solid #34465e; border-radius: 8px; }
QListWidget::item { padding: 14px 10px; }
QListWidget::item:selected { background: #17685e; }
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--demo-file", action="append", default=[])
    parser.add_argument("--quit-after", type=int, help="Cierre automático para verificación, en milisegundos")
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    app.setApplicationName("Tecnomata IPTV")
    app.setDesktopFileName("tecnomata-iptv")
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    window = Window(args.demo or bool(args.demo_file), args.demo_file)
    window.show()
    if args.quit_after:
        QTimer.singleShot(args.quit_after, window.close)
        window.destroyed.connect(app.quit)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
