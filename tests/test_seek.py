from types import SimpleNamespace
from PySide6.QtWidgets import QApplication
from tecnomata_iptv.app import Window
from tecnomata_iptv.player import VideoWidget


def test_seek_checks_availability_and_clamps_absolute_target():
    app = QApplication.instance() or QApplication([])
    video = VideoWidget()
    calls = []
    video.engine = SimpleNamespace(duration=100, seekable=True, command=lambda *args:calls.append(args))
    video.pending_url = 'synthetic.mp4'
    assert not video.seek_to(25)
    video.media_ready = True
    assert video.seek_to(25)
    assert calls[-1] == ('seek', 25, 'absolute+exact')
    video.seek_to(-10)
    assert calls[-1][1] == 0
    video.seek_to(150)
    assert calls[-1][1] == 100
    video.engine.seekable = False
    assert not video.seek_to(20)
    video.engine = None
    video.dispose()


def test_timeline_only_for_current_vod_or_episode_and_resets():
    app = QApplication.instance() or QApplication([])
    window = Window(demo=True, restore=False)
    calls = []
    window.video.seek_to = calls.append
    window.video.pending_url = 'synthetic.mp4'
    for kind in ('vod','series'):
        window.playing_kind = kind
        window.update_position({'position':65,'duration':120,'seekable':True})
        window.toggle_timeline()
        assert not window.timeline.isHidden()
        assert window.elapsed.text() == '01:05' and window.total_time.text() == '02:00'
        window.seek_fraction(250)
        assert calls[-1] == 30
        window.timeline.hide()
    window.section('live')  # Browsing TV does not change the active episode.
    window.update_position({'position':1,'duration':120,'seekable':True})
    assert window.seek_slider.isEnabled()
    window.playing_kind = 'live'
    window.toggle_timeline()
    assert window.timeline.isHidden()
    window.update_position({'position':1,'duration':120,'seekable':True})
    assert not window.seek_slider.isEnabled()
    window.update_position({})
    assert window.elapsed.text() == '00:00'
    window.close()
