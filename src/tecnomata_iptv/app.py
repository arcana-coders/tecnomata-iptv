import argparse
import sys
import json
import os
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Qt, QTimer
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QLineEdit, QComboBox, QListWidget,
    QListWidgetItem, QSplitter, QSlider, QDialog, QFormLayout, QDialogButtonBox, QCheckBox)

from .xtream import Account, XtreamClient, ServiceError
from .player import VideoWidget
from .catalog import CatalogCache, KINDS
from .accounts import AccountStore, StorageError


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
        except (ServiceError, StorageError) as exc:
            self.signals.error.emit(str(exc))
        except Exception:
            # Never expose exception text: HTTP URLs contain account secrets.
            self.signals.error.emit("No se pudo completar la operación. Revisa la conexión y vuelve a intentar.")


class Login(QDialog):
    def __init__(self, parent, account=None):
        super().__init__(parent)
        self.setWindowTitle("Conectar mi servicio")
        self.setMinimumWidth(440)
        form = QFormLayout(self)
        form.addRow(QLabel("Puedes recordar tu cuenta en el almacén seguro de Linux."))
        self.server = QLineEdit()
        self.server.setPlaceholderText("http://servidor:puerto")
        self.user = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        for label, widget in [("Servidor", self.server), ("Usuario", self.user), ("Contraseña", self.password)]:
            form.addRow(label, widget)
        if account:
            self.server.setText(account.server)
            self.user.setText(account.username)
            self.password.setText(account.password)
        self.remember = QCheckBox("Recordar mi cuenta")
        self.remember.setChecked(True)
        form.addRow(self.remember)
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
    def __init__(self, demo=False, demo_files=(), restore=True, account_store=None):
        super().__init__()
        self.setWindowTitle("Tecnomata IPTV")
        self.setObjectName("tecnomata-iptv")
        self.resize(1200, 760)
        self.client = None
        self.cache = None
        self.account_store = account_store or AccountStore()
        self.saved_account = None
        self.foreground_jobs = set()
        self.pending_section = None
        self.failed_sections = set()
        self.category_choices = {}
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
        self.forget_button = QPushButton("Olvidar cuenta")
        self.forget_button.clicked.connect(self.forget_account)
        self.forget_button.hide()
        top.addWidget(self.forget_button)
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
        self.refresh_button = QPushButton("Actualizar listas")
        self.refresh_button.clicked.connect(self.refresh_catalogs)
        self.refresh_button.setEnabled(False)
        filters.addWidget(self.refresh_button)
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
        self.preload_status = QLabel()
        self.preload_status.setWordWrap(True)
        layout.addWidget(self.preload_status)
        self.account_note = QLabel()
        self.account_note.setWordWrap(True)
        layout.addWidget(self.account_note)
        self.escape = QShortcut(QKeySequence("Escape"), self)
        self.escape.activated.connect(self.exit_fullscreen)
        self.fkey = QShortcut(QKeySequence("F"), self)
        self.fkey.activated.connect(self.fullscreen)
        self.diagnostic_timer = QTimer(self)
        self.diagnostic_timer.timeout.connect(self.save_diagnostic)
        self.diagnostic_timer.start(1000)
        self.section("live")
        if restore and not self.demo:
            QTimer.singleShot(0, self.restore_account)

    def sync_busy(self):
        # Preloading must not lock browsing or playback of loaded sections.
        foreground = bool(self.foreground_jobs)
        for widget in (self.navigation, self.items, self.back):
            widget.setEnabled(not foreground)
        self.category.setEnabled(not foreground and not self.in_episodes)
        self.connect_button.setEnabled(not self.jobs)
        self.forget_button.setEnabled(not self.jobs)
        self.refresh_button.setEnabled(self.client is not None and not self.jobs)

    def submit(self, function, callback, background=False, on_error=None):
        job = Job(function)
        self.jobs.add(job)
        if not background:
            self.foreground_jobs.add(job)
            self.status.setText("Cargando…")
        self.sync_busy()
        def finish(result=None, error=None):
            self.jobs.discard(job)
            self.foreground_jobs.discard(job)
            self.sync_busy()
            if error:
                (on_error or self.show_error)(error)
            else:
                if not background:
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
        dialog = Login(self, self.client.account if self.client else self.saved_account)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        account = dialog.account
        remember = dialog.remember.isChecked()
        dialog.password.clear()
        dialog.deleteLater()
        self.connect_account(account, remember, update_store=True)

    def restore_account(self):
        def loaded(account):
            if account:
                self.saved_account = account
                self.forget_button.show()
                self.connect_account(account, True)
        self.submit(self.account_store.load, loaded,
                    on_error=lambda message: self.account_note.setText(message))

    def connect_account(self, account, remember=True, update_store=False):
        client = XtreamClient(account)
        def connect():
            try:
                client.authenticate()
                note = "Cuenta recordada en el almacén seguro de Linux." if remember else "Cuenta sólo para esta sesión."
                remembered = remember
                if update_store:
                    try:
                        if remember:
                            self.account_store.save(account)
                        else:
                            self.account_store.forget()
                    except StorageError as exc:
                        note = str(exc)
                        remembered = False
                return client, note, remembered
            except Exception:
                client.close()
                raise
        def connected(result):
            new_client, note, remembered = result
            self.video.stop()
            if self.client:
                self.client.close()
            self.client = new_client
            self.cache = CatalogCache(new_client)
            self.saved_account = account if remembered else None
            self.account_note.setText(note)
            self.forget_button.setVisible(remembered or note.startswith("No se pudo borrar"))
            self.failed_sections.clear()
            self.category_choices.clear()
            self.demo = False
            self.connect_button.setText("Cambiar servicio")
            self.section(self.kind)
        self.submit(connect, connected)

    def forget_account(self):
        def forgotten(_):
            self.video.stop()
            if self.client:
                self.client.close()
            self.client = None
            self.cache = None
            self.saved_account = None
            self.failed_sections.clear()
            self.category_choices.clear()
            self.forget_button.hide()
            self.account_note.setText("Cuenta olvidada.")
            self.connect_button.setText("Conectar mi servicio")
            self.preload_status.clear()
            self.section("live")
            self.sync_busy()
        self.submit(self.account_store.forget, forgotten)

    def refresh_catalogs(self):
        if self.client and not self.jobs:
            self.cache = CatalogCache(self.client)
            self.failed_sections.clear()
            self.section(self.kind)

    def preload_next(self):
        if not self.cache or self.pending_section:
            return
        pending = [kind for kind in dict.fromkeys((self.kind, *KINDS))
                   if kind not in self.cache.sections and kind not in self.failed_sections]
        if not pending:
            self.preload_status.setText("Listas precargadas." if not self.failed_sections else
                                        "Alguna lista no se pudo precargar. Usa Actualizar listas para reintentar.")
            return
        kind = pending[0]
        self.pending_section = kind
        labels = {"live": "TV en vivo", "vod": "películas", "series": "series"}
        self.preload_status.setText(f"Precargando {labels[kind]}…")
        def loaded(section):
            self.pending_section = None
            if self.kind == kind and not self.in_episodes:
                self.display_section(section)
            self.preload_next()
        def failed(message):
            self.pending_section = None
            self.failed_sections.add(kind)
            if self.kind == kind:
                self.show_error(message)
            self.preload_next()
        cache = self.cache
        self.submit(lambda: cache.section(kind), loaded, background=True, on_error=failed)

    def display_section(self, section):
        selected = self.category_choices.get(self.kind)
        self.category.blockSignals(True)
        self.category.clear()
        self.category.addItem("Todas las categorías", None)
        for row in section.categories:
            self.category.addItem(str(row.get("category_name", "Sin nombre")), row.get("category_id"))
        index = self.category.findData(selected)
        self.category.setCurrentIndex(max(0, index))
        self.category.blockSignals(False)
        self.set_rows(section.filtered(self.category.currentData()))

    def section(self, kind):
        self.kind = kind
        self.in_episodes = False
        self.sync_busy()
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
            if kind in self.cache.sections:
                self.display_section(self.cache.sections[kind])
            else:
                self.status.setText("No se pudo cargar esta lista. Usa Actualizar listas para reintentar."
                                    if kind in self.failed_sections else "Esta lista se está precargando…")
            self.preload_next()
        else:
            self.status.setText("Conecta tu servicio para cargar TV en vivo, películas y series. Doble clic para reproducir.")

    def load_catalog(self):
        if not self.client or self.in_episodes:
            return
        category = self.category.currentData()
        self.category_choices[self.kind] = category
        if self.kind in self.cache.sections:
            self.set_rows(self.cache.sections[self.kind].filtered(category))

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
                self.sync_busy()
                self.back.show()
                self.search.clear()
                self.set_rows(episodes)
            if self.demo:
                loaded([{"name": "T1 · E1 · Episodio de prueba", "stream_id": 1}])
            else:
                series_id = row.get("series_id")
                if str(series_id) in self.cache.episode_lists:
                    loaded(self.cache.episode_lists[str(series_id)])
                else:
                    cache = self.cache
                    self.submit(lambda: cache.episodes(series_id), loaded)
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
