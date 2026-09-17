"""Native libmpv resume of two movies and two episodes across Window reopen."""
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from tecnomata_iptv.app import Window, configure_appearance
from tecnomata_iptv.library import LibraryStore

root = Path(__file__).resolve().parents[1]
app = QApplication(sys.argv[:1]); configure_appearance(app)
temporary = TemporaryDirectory()
path = Path(temporary.name)/'library.sqlite3'
items = [('vod',1,'',3,2,2,150),('vod',2,'',7,1,'no',90),
         ('episode',1,'11',4,2,1,120),('episode',1,'12',8,1,2,180)]
state = {'index':0,'stage':'load','reopen':False,'attempts':0}

def new_window():
    window = Window(demo=True,demo_files=[root/'runtime/sub-size-demo.mkv'],restore=False,library_store=LibraryStore(path))
    window.show(); return window
window = new_window()

def open_item():
    global window
    kind, identity, parent, *_ = items[state['index']]
    window.section('vod')
    window.play_content({'stream_id':identity,'name':f'Fiction {kind} {identity} {parent}'},kind,parent)
    state['stage']='load'; state['attempts']=0

def check():
    global window
    try:
        state['attempts']+=1
        kind, identity, parent, position, audio, sub, size = items[state['index']]
        engine = window.video.engine
        if state['stage']=='load' and window.video.media_ready and len(window.video.media_info.get('audio',[]))==2:
            engine.pause=True
            if state['reopen']:
                if window.pending_resume or window.resume_target is not None:
                    QTimer.singleShot(100,check); return
                assert abs((engine.time_pos or 0)-position)<.5, (engine.time_pos,position)
                assert engine.aid == audio and (engine.sid == sub or sub == "no" and engine.sid is False), (engine.aid,engine.sid,audio,sub)
                assert abs(engine.sub_scale-size/100)<.01, (engine.sub_scale,size)
                state['stage']='next'
            else:
                window.video.select_track('audio',audio); window.video.select_track('sub',sub)
                window.adjust_subtitle_size(size-window.sub_size_percent)
                assert window.video.seek_to(position)
                state['stage']='seek'
        elif state['stage']=='seek' and abs((engine.time_pos or 0)-position)<.3:
            window.save_progress(force=True)
            state['stage']='next'
        if state['stage']=='next':
            state['index']+=1
            if state['index']==len(items):
                window.close()
                if state['reopen']:
                    print('Progress smoke: PASS (two movies, two episodes, reopen, independent position/audio/subtitle/size)')
                    app.quit(); return
                state.update(index=0,reopen=True)
                window = new_window()
            open_item()
        if state['attempts']>120: raise AssertionError('timeout')
        QTimer.singleShot(100,check)
    except Exception as exc:
        print('Progress smoke: FAIL',type(exc).__name__,str(exc),'item',state['index'],'stage',state['stage'])
        window.close(); app.exit(1)
app.setQuitOnLastWindowClosed(False)
QTimer.singleShot(300,open_item);QTimer.singleShot(500,check)
result = app.exec(); temporary.cleanup(); raise SystemExit(result)
