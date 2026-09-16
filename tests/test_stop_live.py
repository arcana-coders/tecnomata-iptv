from PySide6.QtWidgets import QApplication
from tecnomata_iptv.app import Window


class Engine:
    def __init__(self):
        self.commands = []
        self.pause = False
    def command(self, *args):
        self.commands.append(args)


def test_stop_closes_source_and_pause_cannot_restart_it():
    app = QApplication.instance() or QApplication([])
    window = Window(demo=True, restore=False)
    engine = Engine()
    window.video.engine = engine
    window.video.pending_url = 'https://example.invalid/live.ts'
    window.playing_kind = 'live'
    window.stop_playback()
    assert engine.commands == [('stop',)]
    assert window.video.pending_url is None
    assert window.video.diagnostic['state'] == 'idle'
    assert window.playing_kind is None
    window.video.toggle_pause()
    assert not engine.pause
    window.video.engine = None
    window.close()


def test_go_live_reopens_playing_channel_even_when_browsing_other_section():
    app = QApplication.instance() or QApplication([])
    window = Window(demo=True, restore=False)
    engine = Engine()
    window.video.engine = engine
    url = 'https://example.invalid/live.ts'
    window.video.pending_url = url
    window.playing_kind = 'live'
    engine.pause = True
    window.section('vod')
    window.catch_up_live()
    assert engine.commands == [('stop',), ('loadfile', url, 'replace')]
    assert not engine.pause
    assert window.video.pending_url == url
    engine.commands.clear()
    window.playing_kind = 'vod'
    window.catch_up_live()
    assert not engine.commands
    window.video.engine = None
    window.close()
