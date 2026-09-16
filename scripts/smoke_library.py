"""Real UI/video with persistent synthetic favorites/recent and design screenshots."""
import sys
import tempfile
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from tecnomata_iptv.app import Window, configure_appearance
from tecnomata_iptv.library import LibraryStore

root = Path(__file__).resolve().parents[1]
app = QApplication(sys.argv[:1])
configure_appearance(app)
folder = tempfile.TemporaryDirectory()
path = Path(folder.name) / 'library.sqlite3'
window = Window(demo=True, demo_files=[root / 'runtime/demo-a.mp4', root / 'runtime/demo-b.mp4'],
                restore=False, library_store=LibraryStore(path))
window.show()
state = {'attempts': 0}


def start():
    window.section('live')
    for index in range(2):
        window.items.setCurrentRow(index)
        window.toggle_favorite()
    window.show_collection('favorites')
    assert window.items.count() == 2
    window.activate(window.items.item(1))
    assert window.collection_view == 'favorites' and window.items.count() == 2
    QTimer.singleShot(100, check)


def check():
    try:
        state['attempts'] += 1
        recent = window.library_rows('recent')
        if (not recent or window.video.frames <= 10) and state['attempts'] < 80:
            QTimer.singleShot(100, check)
            return
        assert len(recent) == 1 and recent[0]['name'] == 'Canal de prueba B'
        assert window.video.frames > 10
        window.grab().save(str(root / 'runtime/metro-player.png'))
        window.show_home()
        QTimer.singleShot(200, finish)
    except Exception as exc:
        print('Library smoke: FAIL', type(exc).__name__)
        window.close()
        app.exit(1)


def finish():
    try:
        window.grab().save(str(root / 'runtime/metro-home.png'))
        window.close()
        reopened = LibraryStore(path)
        assert len(reopened.rows('demo', 'favorites')) == 2
        assert len(reopened.rows('demo', 'recent')) == 1
        reopened.close()
        print('Library smoke: PASS (favorites stay visible while playing, successful play recorded, persistent favorites/recent, home/player captures)')
        app.quit()
    except Exception as exc:
        print('Library smoke finish: FAIL', type(exc).__name__)
        app.exit(1)


QTimer.singleShot(300, start)
result = app.exec()
folder.cleanup()
raise SystemExit(result)
