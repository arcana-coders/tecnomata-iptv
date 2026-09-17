from types import SimpleNamespace
from PySide6.QtWidgets import QApplication
from tecnomata_iptv.app import Window


def test_subtitle_size_and_visibility_do_not_change_audio_or_source():
    app = QApplication.instance() or QApplication([])
    window = Window(demo=True, restore=False)
    video = window.video
    video.engine = SimpleNamespace(aid=12,sid='no',sub_visibility=False,sub_scale=1.)
    video.pending_url = 'synthetic.mkv'
    video.media_ready = True
    video.media_info = {'sub':[{'id':19}], 'audio':[{'id':12}]}
    window.update_media(video.media_info)
    window.sub_larger.click()
    assert video.engine.sub_scale == 1.1 and window.sub_size_label.text() == '110%'
    window.sub_smaller.click()
    assert video.engine.sub_scale == 1.
    video.select_track('sub',19)
    assert video.engine.sid == 19 and video.engine.sub_visibility
    assert video.engine.aid == 12 and video.pending_url == 'synthetic.mkv'
    video.select_track('sub','no')
    assert not video.engine.sub_visibility
    for _ in range(30): window.adjust_subtitle_size(10)
    assert window.sub_size_percent == 250
    for _ in range(30): window.adjust_subtitle_size(-10)
    assert window.sub_size_percent == 50
    video.reset_media()
    assert not window.sub_larger.isEnabled()
    video.engine = None
    window.close()


def test_subtitle_preference_restores_from_isolated_settings(tmp_path, monkeypatch):
    from PySide6.QtCore import QSettings
    from tecnomata_iptv import app as module
    from tecnomata_iptv.library import LibraryStore
    app = QApplication.instance() or QApplication([])
    settings = QSettings(str(tmp_path/'preferences.ini'), QSettings.Format.IniFormat)
    monkeypatch.setattr(module,'QSettings',lambda *args:settings)
    window = Window(restore=False,library_store=LibraryStore(':memory:'),mpris_enabled=False)
    window.adjust_subtitle_size(20)
    window.close()
    reopened = Window(restore=False,library_store=LibraryStore(':memory:'),mpris_enabled=False)
    assert reopened.sub_size_percent == 120 and reopened.video.subtitle_scale == 1.2
    reopened.close()
