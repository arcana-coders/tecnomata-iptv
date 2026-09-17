from dbus_fast import Variant
from tecnomata_iptv.mpris import Player


def test_mpris_metadata_controls_and_track_guard():
    calls = []
    player = Player(lambda *args:calls.append(args))
    player.update({'Metadata':{'xesam:title':Variant('s','Fictional movie'),
        'mpris:trackid':Variant('o','/tecnomata/iptv/track/1')},
        'PlaybackStatus':'Playing','CanSeek':True,'Position':5_000_000})
    assert player.Metadata['xesam:title'].value == 'Fictional movie'
    assert 'xesam:url' not in player.Metadata
    player.PlayPause(); assert calls[-1] == ('toggle',None)
    player.Seek(-2_000_000); assert calls[-1] == ('seek',3.)
    count = len(calls)
    player.SetPosition('/tecnomata/iptv/track/0',10_000_000)
    assert len(calls) == count
    player.SetPosition('/tecnomata/iptv/track/1',10_000_000)
    assert calls[-1] == ('seek',10.)
    player.Volume = .37
    assert calls[-1] == ('volume',.37)
    player.update({'Metadata':{},'PlaybackStatus':'Stopped','CanSeek':False})
    assert player.Metadata == {} and player.PlaybackStatus == 'Stopped'
    count = len(calls); player.Seek(1_000_000); assert len(calls) == count
