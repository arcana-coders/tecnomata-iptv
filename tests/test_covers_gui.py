from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from tecnomata_iptv.app import Window
from tecnomata_iptv.library import LibraryStore
from tecnomata_iptv.details import ContentDetailDialog


def create_window():
    _app = QApplication.instance() or QApplication([])
    lib = LibraryStore(':memory:')
    win = Window(library_store=lib, demo=True, restore=False)
    win.show()
    return win


def test_entering_vod_when_stopped_shows_covers_view():
    win = create_window()
    win.show_player()
    assert win.playback_status == "Stopped"

    # Enter live: right_stack should show player (index 0)
    win.section("live")
    assert win.right_stack.currentIndex() == 0
    assert not win.to_covers_button.isVisible()

    # Enter vod: since playback is stopped, right_stack should automatically show covers (index 1)
    win.section("vod")
    assert win.right_stack.currentIndex() == 1
    assert win.covers_container.isVisible()
    assert win.cover_grid.count() > 0
    win.close()


def test_entering_vod_when_playing_keeps_player_and_shows_button():
    win = create_window()
    win.show_player()
    win.playback_status = "Playing"
    win.now.setText("Canal Deportivo")

    # Enter vod while video is playing
    win.section("vod")
    # Player stays visible
    assert win.right_stack.currentIndex() == 0
    # "Ir a carátulas" button is visible under screen
    assert win.to_covers_button.isVisible()

    # Click "Ir a carátulas"
    win.to_covers_button.click()
    assert win.right_stack.currentIndex() == 1
    assert "Canal Deportivo" in win.back_to_player_button.text()

    # Click "Volver al reproductor"
    win.back_to_player_button.click()
    assert win.right_stack.currentIndex() == 0
    win.close()


def test_poster_activation_opens_detail_dialog(monkeypatch):
    win = create_window()
    win.section("vod")
    assert win.cover_grid.count() > 0

    opened_dialogs = []

    def mock_exec(dialog_self):
        opened_dialogs.append(dialog_self)
        return 0

    monkeypatch.setattr(ContentDetailDialog, "exec", mock_exec)

    # Click first poster in grid
    first_item = win.cover_grid.item(0)
    win.cover_grid.itemActivated.emit(first_item)

    assert len(opened_dialogs) == 1
    dialog = opened_dialogs[0]
    assert dialog.row["name"] == "Película de prueba"
    assert dialog.kind == "vod"
    win.close()


def test_detail_dialog_play_starts_playback_and_shows_player():
    win = create_window()
    row = {"name": "Test Movie", "stream_id": 1, "plot": "A great movie."}
    played = []

    def mock_play(restart=False):
        played.append(restart)

    dialog = ContentDetailDialog(
        parent=win,
        row=row,
        kind="vod",
        cover_cache=win.cover_cache,
        on_play=mock_play,
    )

    # Click play button
    dialog._play()
    assert played == [False]
    dialog.close()
    win.close()


def test_detail_dialog_favorite_toggle():
    win = create_window()
    row = {"name": "Test Movie", "stream_id": 1}
    fav_state = [False]

    def mock_toggle():
        fav_state[0] = not fav_state[0]
        return fav_state[0]

    dialog = ContentDetailDialog(
        parent=win,
        row=row,
        kind="vod",
        cover_cache=win.cover_cache,
        is_fav=False,
        on_toggle_favorite=mock_toggle,
    )

    dialog._toggle_fav()
    assert fav_state[0] is True
    assert "★" in dialog.fav_btn.text()

    dialog._toggle_fav()
    assert fav_state[0] is False
    assert "☆" in dialog.fav_btn.text()
    dialog.close()
    win.close()
