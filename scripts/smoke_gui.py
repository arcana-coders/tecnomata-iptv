"""Prueba gráfica real; requiere sesión Wayland/X11 y los dos videos de runtime."""
import json
import sys
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from tecnomata_iptv.app import Window, configure_appearance

root = Path(__file__).resolve().parents[1]
app = QApplication(sys.argv[:1])
configure_appearance(app)
window = Window(True, [root / "runtime/demo-a.mp4", root / "runtime/demo-b.mp4"])
window.show()
window.show_player()
state = {"changes": 0, "engine": None, "widget": id(window.video), "frames_start": 0}
failed = []
window.video.failed.connect(failed.append)


def switch():
    try:
        assert not failed, failed
        assert window.video.engine is not None, window.video.init_error
        if state["engine"] is None:
            state["engine"] = id(window.video.engine)
        assert state["engine"] == id(window.video.engine)
        assert state["widget"] == id(window.video)
        window.activate(window.items.item(state["changes"] % 2))
        state["changes"] += 1
        if state["changes"] < 8:
            QTimer.singleShot(500, switch)
        else:
            QTimer.singleShot(1000, finish)
    except Exception as exc:
        failed.append(str(exc))
        finish()


def finish():
    try:
        assert not failed, failed
        assert window.video.frames > 10, "No hay frames renderizados"
        assert len([w for w in app.topLevelWidgets() if w.isVisible()]) == 1, "Hay más de una ventana Qt visible"
        image = window.video.grabFramebuffer()
        assert not image.isNull()
        center = image.pixelColor(image.width() // 2, image.height() // 2)
        assert center.red() + center.blue() > 50, "Video negro; se esperaba el clip morado"
        assert window.video.engine.playlist_count == 1
        # Navigation and episodes are usable after switching video.
        window.section("series")
        window.activate(window.items.item(0))
        assert window.in_episodes and window.items.count() == 1
        window.back.click()
        assert not window.in_episodes
        window.section("vod")
        window.search.setText("inexistente")
        assert window.items.count() == 0
        window.search.clear()
        assert window.items.count() == 1
        window.section("live")
        window.fullscreen()
        window.exit_fullscreen()
        window.grab().save(str(root / "runtime/prototype.png"))
        print(json.dumps({"result": "PASS", "switches": state["changes"],
            "rendered_frames": window.video.frames, "same_engine": True,
            "same_widget": True, "qt_windows": len([w for w in app.topLevelWidgets() if w.isVisible()]),
            "center_rgb": [center.red(), center.green(), center.blue()],
            "playlist_count": window.video.engine.playlist_count}))
    except Exception as exc:
        print(json.dumps({"result": "FAIL", "error": str(exc)}))
        failed.append(str(exc))
    window.close()
    app.exit(1 if failed else 0)


QTimer.singleShot(800, switch)
raise SystemExit(app.exec())
