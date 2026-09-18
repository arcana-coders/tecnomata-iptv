from types import SimpleNamespace
from PySide6.QtWidgets import QApplication
from tecnomata_iptv.app import Window
from tecnomata_iptv.library import LibraryStore
from tecnomata_iptv.progress import resolve_track


def test_multiple_movies_episodes_accounts_survive_reopen_and_history_pruning(tmp_path):
    path = tmp_path/'library.sqlite3'
    db = LibraryStore(path)
    for kind, identity, parent, position in [('vod',1,'',17),('vod',2,'',23),('episode',1,'4',31),('episode',1,'5',41)]:
        db.save_progress('account',kind,{'stream_id':identity},parent,position=position,duration=100,
                         audio={'id':2,'lang':'eng'},subtitle='no',subtitle_size=150)
    db.save_progress('other','vod',{'stream_id':1},position=7,duration=100)
    for i in range(110):
        db.played('account','vod',{'stream_id':i})
    db.close()
    db = LibraryStore(path)
    assert len(db.rows('account','recent')) == 100
    for kind, identity, parent, position in [('vod',1,'',17),('vod',2,'',23),('episode',1,'4',31),('episode',1,'5',41)]:
        item = db.progress('account',kind,{'stream_id':identity},parent)
        assert item['position'] == position and item['audio']['id'] == 2
        assert item['subtitle'] == 'no' and item['subtitle_size'] == 150
    assert db.progress('other','vod',{'stream_id':1})['position'] == 7
    assert db.progress('account','live',{'stream_id':1}) is None
    db.close()


def test_additive_migration_keeps_existing_library(tmp_path):
    path = tmp_path/'library.sqlite3'
    db = LibraryStore(path)
    db.toggle('account','vod',{'stream_id':1,'name':'Fiction'})
    db.db.execute('DROP TABLE progress'); db.db.commit(); db.close()
    db = LibraryStore(path)
    assert db.rows('account','favorites')[0]['name'] == 'Fiction'
    assert db.progress('account','vod',{'stream_id':1}) is None
    db.close()


def test_track_matching_handles_reordered_ids_without_wrong_language():
    saved = {'id':2,'lang':'eng','codec':'aac'}
    assert resolve_track(saved,[{'id':2,'lang':'spa','codec':'aac'},{'id':1,'lang':'eng','codec':'aac'}]) == 1
    assert resolve_track(saved,[{'id':2,'lang':'spa','codec':'aac'}]) is None
    assert resolve_track('no',[]) == 'no'


def make_window(tmp_path):
    app = QApplication.instance() or QApplication([])
    window = Window(demo=True,demo_files=['synthetic.mp4'],restore=False,library_store=LibraryStore(tmp_path/'library.sqlite3'))
    return window


def fake_loaded(window, position=0):
    calls = []
    window.video.engine = SimpleNamespace(time_pos=position,duration=100,seekable=True,
        command=lambda *args:calls.append(args),aid=1,sid=1,sub_scale=1,sub_visibility=True)
    window.video.media_ready = True
    window.video.media_info = {'audio':[{'id':1,'lang':'spa'},{'id':2,'lang':'eng'}],
                               'sub':[{'id':1,'lang':'spa'},{'id':2,'lang':'eng'}],'aid':1,'sid':1}
    window.video.read_media = lambda:None
    return calls


def cleanup(window):
    window.video.engine = None
    window.close()


def test_restore_waits_for_seek_confirmation_and_preserves_bookmark_on_failure(tmp_path):
    window = make_window(tmp_path)
    row = {'stream_id':1,'name':'Fiction'}
    window.library.save_progress('demo','vod',row,position=40,duration=100,audio={'id':2,'lang':'eng'},subtitle='no',subtitle_size=150)
    window.play_content(row,'vod')
    calls = fake_loaded(window)
    window.update_position({'position':0,'duration':100,'seekable':True})
    assert calls[-1] == ('seek',40,'absolute+exact')
    assert window.video.engine.aid == 2 and window.video.engine.sid == 'no'
    assert window.sub_size_percent == 150
    window.save_progress(force=True)
    assert window.library.progress('demo','vod',row)['position'] == 40
    window.resume_deadline = 0
    window.update_position({'position':0,'duration':100,'seekable':True})
    assert window.progress_blocked
    assert window.library.progress('demo','vod',row)['position'] == 40
    window.restart_content()
    window.update_position({'position':0,'duration':100,'seekable':True})
    window.save_progress(force=True)
    assert window.library.progress('demo','vod',row)['position'] == 0
    cleanup(window)


def test_stop_pause_close_and_eof_save_separately(tmp_path):
    window = make_window(tmp_path)
    row = {'stream_id':1,'name':'One'}
    window.play_content(row,'vod'); fake_loaded(window,33)
    window.playback_state('paused')
    assert window.library.progress('demo','vod',row)['position'] == 33
    window.video.stop = lambda:None
    window.stop_playback()
    row2 = {'stream_id':2,'name':'Two'}
    window.video.engine = None
    window.play_content(row2,'vod'); fake_loaded(window,99)
    window.update_position({'position':99,'duration':100,'seekable':True})
    window.playback_state('ended')
    assert window.library.progress('demo','vod',row2)['completed'] == 1
    window.save_progress(force=True)
    assert window.library.progress('demo','vod',row2)['position'] == 0
    assert window.library.progress('demo','vod',row)['position'] == 33
    cleanup(window)


def test_failed_load_does_not_erase_previous_progress(tmp_path):
    window = make_window(tmp_path)
    row = {'stream_id':1,'name':'Fiction'}
    window.library.save_progress('demo','vod',row,position=50,duration=100)
    window.play_content(row,'vod')
    window.update_position({}); window.save_progress(force=True)
    assert window.library.progress('demo','vod',row)['position'] == 50
    window.close()
