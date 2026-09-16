from types import SimpleNamespace
from PySide6.QtWidgets import QApplication
from tecnomata_iptv.media import describe_video, track_label
from tecnomata_iptv.player import VideoWidget
from tecnomata_iptv.app import Window


def test_quality_uses_dimensions_and_missing_data_is_explicit():
    assert describe_video({}) == 'Sin reproducción'
    assert describe_video({'width': None}) == 'Resolución no disponible'
    assert describe_video({'width': 1920, 'height': 1080, 'fps': 29.97, 'codec': 'h264'}) == 'Full HD · 1920 × 1080  ·  29.97 fps  ·  H264'
    assert 'nan' not in describe_video({'width': 640, 'height': 360, 'fps': float('nan')})
    assert describe_video({'width': 3840, 'height': 2160}).startswith('UHD')
    assert 'Idioma no indicado' in track_label({'id': 2, 'codec': 'aac'})
    assert 'Español' in track_label({'id': 7, 'lang': 'spa'})


def test_track_ids_selection_and_clearing_do_not_use_list_positions():
    app = QApplication.instance() or QApplication([])
    window = Window(demo=True, restore=False)
    video = window.video
    video.engine = SimpleNamespace(video_params={'w': 1280, 'h': 720}, container_fps=25,
        video_codec='h264', aid=7, sid='no', track_list=[
            {'type': 'audio', 'id': 7, 'lang': 'spa'},
            {'type': 'audio', 'id': 12, 'lang': 'eng'},
            {'type': 'sub', 'id': 19, 'lang': 'spa'}])
    video.media_ready = True
    video.read_media()
    assert window.audio_tracks.currentData() == 7
    assert window.subtitle_tracks.currentData() == 'no'
    video.select_track('audio', 12)
    assert video.engine.aid == 12 and window.audio_tracks.currentData() == 12
    video.select_track('sub', 19)
    assert video.engine.sid == 19 and window.subtitle_tracks.currentData() == 19
    video.select_track('sub', 'no')
    assert video.engine.sid == 'no'
    video.select_track('audio', 999)
    assert video.engine.aid == 12
    video.reset_media()
    assert not window.audio_tracks.isEnabled()
    assert not window.subtitle_tracks.isEnabled()
    assert window.quality.text() == 'Sin reproducción'
    video.select_track('audio', 7)
    assert video.engine.aid == 12
    video.engine = None
    window.close()
    window.deleteLater()
