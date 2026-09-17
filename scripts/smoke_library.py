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
        engine_id = id(window.video.engine)
        window.toggle_list()
        app.processEvents()
        assert window.reveal_button.isVisible() and not window.left_panel.isVisible()
        assert window.splitter.sizes()[1] == 36
        assert window.reveal_button.width() > 0
        window.grab().save(str(root / 'runtime/springfield-hidden-list.png'))
        window.reveal_button.click()
        assert window.left_panel.isVisible() and not window.hidden_list_rail.isVisible()
        assert id(window.video.engine) == engine_id
        assert all(tile.example is not None and not tile.example.isNull() for tile in window.home_tiles.values())
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
        engine = id(window.video.engine)
        source = window.video.pending_url
        for key in ('mcfly', 'retro', 'dog-eyes', 'springfield'):
            window.theme_selector.setCurrentIndex(window.theme_selector.findData(key))
            app.processEvents()
            assert id(window.video.engine) == engine and window.video.pending_url == source
            window.grab().save(str(root / f'runtime/theme-{key}.png'))
            window.show_player()
            app.processEvents()
            center = window.hide_list_button.mapTo(window.left_panel, window.hide_list_button.rect().center())
            assert abs(center.y() - window.left_panel.height()/2) < 2
            window.grab().save(str(root / f'runtime/player-{key}.png'))
            window.show_home()
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
