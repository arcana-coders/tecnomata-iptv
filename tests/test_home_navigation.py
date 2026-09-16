from PySide6.QtWidgets import QApplication
from tecnomata_iptv.app import Window


def test_empty_collection_tiles_hide_and_data_reveals_them():
    app = QApplication.instance() or QApplication([])
    window = Window(demo=True, restore=False)
    assert window.home_favorites.isHidden() and window.home_recent.isHidden()
    window.section('live')
    window.items.setCurrentRow(0)
    window.toggle_favorite()
    assert not window.home_favorites.isHidden()
    assert window.home_recent.isHidden()
    window.library.played('demo', 'vod', {'name': 'Movie', 'stream_id': 10})
    window.update_home()
    assert not window.home_recent.isHidden()
    assert 'Movie' in window.home_recent.text()
    window.toggle_favorite()
    assert window.home_favorites.isHidden()
    assert not window.home_recent.isHidden()
    window.close()


def test_reveal_tab_restores_list_without_changing_video_or_selection():
    app = QApplication.instance() or QApplication([])
    window = Window(demo=True, restore=False)
    window.section('live')
    window.items.setCurrentRow(1)
    video_id = id(window.video)
    window.video.pending_url = 'synthetic.ts'
    window.toggle_list()
    assert window.left_panel.isHidden()
    assert not window.hidden_list_rail.isHidden()
    assert not window.list_button.isChecked()
    window.reveal_button.click()
    assert not window.left_panel.isHidden() and window.hidden_list_rail.isHidden()
    assert window.items.currentRow() == 1
    assert id(window.video) == video_id and window.video.pending_url == 'synthetic.ts'
    window.show_home()
    assert window.home_button.isChecked() and not window.player_button.isChecked()
    assert window.list_button.isHidden()
    window.show_player()
    assert window.player_button.isChecked() and not window.home_button.isChecked()
    window.toggle_list()
    window.focus_search()
    assert not window.left_panel.isHidden() and window.hidden_list_rail.isHidden()
    window.close()


def test_example_returns_after_preview_is_cleared():
    from PySide6.QtGui import QPixmap, QColor
    from tecnomata_iptv.widgets import HomeTile
    app = QApplication.instance() or QApplication([])
    tile = HomeTile('TV\nExample', '#101010')
    tile.resize(220, 220)
    example = QPixmap(220, 220)
    example.fill(QColor('red'))
    tile.set_example(example)
    tile.show()
    app.processEvents()
    assert tile.grab().toImage().pixelColor(110, 10).red() > 200
    preview = QPixmap(220, 220)
    preview.fill(QColor('blue'))
    tile.preview = preview
    tile.update()
    app.processEvents()
    assert tile.grab().toImage().pixelColor(110, 10).blue() > 200
    tile.preview = None
    tile.update()
    app.processEvents()
    color = tile.grab().toImage().pixelColor(110, 10)
    assert color.red() > 200 and color.blue() == 0
    tile.close()
