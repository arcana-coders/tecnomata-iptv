from tecnomata_iptv.quality import classify, probe_stream


class FakeEngine:
    """Stand-in for mpv.MPV: no real libmpv/network involved in these tests."""
    def __init__(self, params=None, raise_on_load=False):
        self.params = params
        self.raise_on_load = raise_on_load
        self.terminated = False
        self._observer = None

    def property_observer(self, _name):
        def decorator(func):
            self._observer = func
            return func
        return decorator

    def command(self, *_args):
        if self.raise_on_load:
            raise RuntimeError('boom')
        if self.params is not None and self._observer:
            self._observer('video-params', self.params)

    def terminate(self):
        self.terminated = True


def test_classify_thresholds():
    assert classify(None) is None
    assert classify(0) is None
    assert classify(479) == 'sd'
    assert classify(720) == 'hd'
    assert classify(1079) == 'hd'
    assert classify(1080) == 'fullhd'
    assert classify(2160) == 'fullhd'


def test_probe_stream_classifies_from_real_video_params():
    engine = FakeEngine(params={'w': 1920, 'h': 1080})
    result = probe_stream('http://example.invalid/1', timeout=1, engine_factory=lambda: engine)
    assert result == (1920, 1080, 'fullhd')
    assert engine.terminated


def test_probe_stream_reports_unknown_when_channel_never_responds():
    engine = FakeEngine(params=None)
    result = probe_stream('http://example.invalid/2', timeout=0.05, engine_factory=lambda: engine)
    assert result == (None, None, None)
    assert engine.terminated


def test_probe_stream_survives_loadfile_error():
    engine = FakeEngine(raise_on_load=True)
    result = probe_stream('bad://', timeout=0.05, engine_factory=lambda: engine)
    assert result == (None, None, None)
    assert engine.terminated
