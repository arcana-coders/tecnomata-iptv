from PySide6.QtCore import Qt, QPoint, QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from tecnomata_iptv.app import Window
from tecnomata_iptv.themes import THEMES
from tecnomata_iptv.widgets import FAVORITE_ROLE


def test_themes_keep_video_source_and_generate_distinct_examples():
    app = QApplication.instance() or QApplication([])
    window = Window(demo=True, restore=False)
    window.video.pending_url = 'synthetic.ts'
    widget = id(window.video)
    images = []
    for key in THEMES:
        window.theme_selector.setCurrentIndex(window.theme_selector.findData(key))
        assert window.theme_key == key
        assert window.video.pending_url == 'synthetic.ts' and id(window.video) == widget
        assert all(not tile.example.isNull() for tile in window.home_tiles.values())
        images.append(window.home_tiles['live'].example.toImage())
    assert all(images[i] != images[j] for i in range(4) for j in range(i))
    assert all(tile.monochrome for tile in window.home_tiles.values())
    window.close()


def test_row_star_toggles_without_playing_and_clear_search_restores_rows():
    app = QApplication.instance() or QApplication([])
    window = Window(demo=True, restore=False)
    window.show()
    window.section('live')
    app.processEvents()
    count = window.items.count()
    rect = window.items.visualItemRect(window.items.item(0))
    point = QPoint(18, rect.center().y())
    QTest.mouseClick(window.items.viewport(), Qt.MouseButton.LeftButton, pos=point)
    assert window.items.item(0).data(FAVORITE_ROLE)
    assert window.video.pending_url is None
    QTest.mouseClick(window.items.viewport(), Qt.MouseButton.LeftButton, pos=point)
    assert not window.items.item(0).data(FAVORITE_ROLE)
    window.search.setText('does-not-exist')
    assert window.items.count() == 0 and window.search.isClearButtonEnabled()
    window.search.clear()
    assert window.items.count() == count
    window.volume.setValue(37)
    assert window.volume_percent.text() == '37%'
    window.close()


def test_theme_preference_restores_from_isolated_settings(tmp_path, monkeypatch):
    from tecnomata_iptv import app as module
    from tecnomata_iptv.library import LibraryStore
    app = QApplication.instance() or QApplication([])
    settings = QSettings(str(tmp_path / 'preferences.ini'), QSettings.Format.IniFormat)
    monkeypatch.setattr(module, 'QSettings', lambda *args: settings)
    window = Window(restore=False, library_store=LibraryStore(':memory:'))
    window.theme_selector.setCurrentIndex(window.theme_selector.findData('mcfly'))
    window.close()
    settings.sync()
    reopened = Window(restore=False, library_store=LibraryStore(':memory:'))
    assert reopened.theme_key == 'mcfly'
    assert settings.value('theme') == 'mcfly'
    reopened.close()
