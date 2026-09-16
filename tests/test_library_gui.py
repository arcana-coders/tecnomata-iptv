from PySide6.QtWidgets import QApplication
from tecnomata_iptv.app import Window
from tecnomata_iptv.library import LibraryStore


def test_favorites_toggle_history_success_and_reopen(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    path = tmp_path / 'library.sqlite3'
    window = Window(demo=True, demo_files=['synthetic.mp4'], restore=False, library_store=LibraryStore(path))
    assert not window.home.isHidden()
    window.section('live')
    window.items.setCurrentRow(1)
    window.toggle_favorite()
    assert window.items.item(1).text().startswith('★ ')
    window.show_collection('favorites')
    assert window.items.count() == 1 and not window.category.isEnabled()
    window.activate(window.items.item(0))
    assert window.playing_kind == 'live'
    assert window.library_rows('recent') == []  # Double click alone is not successful playback.
    window.playback_state('Reproduciendo')
    assert window.library_rows('recent')[0]['name'] == 'Canal de prueba B'
    window.playback_state('Reproduciendo')
    assert len(window.library_rows('recent')) == 1
    window.show_home()
    assert 'Canal de prueba B' in window.home_recent.text()
    window.close()
    second = Window(demo=True, restore=False, library_store=LibraryStore(path))
    second.show_collection('recent')
    assert second.items.count() == 1
    second.show_collection('favorites')
    second.items.setCurrentRow(0)
    second.toggle_favorite()
    assert second.items.count() == 0
    assert len(second.library_rows('recent')) == 1
    second.close()


def test_series_and_episode_favorites_reopen_correct_context():
    app = QApplication.instance() or QApplication([])
    window = Window(demo=True, demo_files=['synthetic.mp4'], restore=False)
    window.section('series')
    window.items.setCurrentRow(0)
    window.toggle_favorite()
    window.activate(window.items.item(0))
    window.items.setCurrentRow(0)
    window.toggle_favorite()
    window.activate(window.items.item(0))
    window.playback_state('Reproduciendo')
    window.show_collection('recent')
    window.activate(window.items.item(0))
    assert window.collection_view == 'recent'
    assert window.pending_history[0] == 'episode' and window.pending_history[2] == '1'
    assert window.playing_kind == 'series'
    window.show_collection('favorites')
    assert window.items.count() == 2
    series_index = next(i for i in range(2) if window.items.item(i).data(256)['_kind'] == 'series')
    window.activate(window.items.item(series_index))
    assert window.in_episodes and window.items.count() == 1
    window.stop_playback()
    assert window.pending_history is None
    window.close()
