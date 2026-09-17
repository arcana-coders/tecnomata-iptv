"""Synthetic two subtitle/audio tracks: rendered scaling and cue timing."""
import sys
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication
from tecnomata_iptv.app import Window, configure_appearance
from tecnomata_iptv.diagnostics import text_value
root=Path(__file__).resolve().parents[1]
app=QApplication(sys.argv[:1]);configure_appearance(app)
window=Window(demo=True,demo_files=[root/'runtime/sub-size-demo.mkv'],restore=False)
window.show()
state={'phase':0,'attempts':0}

def glyph_width():
    image=window.video.grabFramebuffer().convertToFormat(QImage.Format.Format_RGBA8888)
    data=bytes(image.constBits()); xs=[]
    for y in range(image.height()//2,image.height()):
        offset=y*image.bytesPerLine()
        for x in range(image.width()):
            i=offset+x*4
            if min(data[i:i+3]) > 210: xs.append(x)
    assert xs, 'no rendered subtitle pixels'
    return max(xs)-min(xs)+1

def start():
    window.section('vod');window.activate(window.items.item(0));QTimer.singleShot(100,check)

def check():
    try:
        state['attempts']+=1
        engine=window.video.engine
        phase=state['phase']
        if phase==0 and len(window.video.media_info.get('sub',[]))==2:
            assert len(window.video.media_info['audio'])==2
            state['audio']=engine.aid
            engine.pause=True
            window.video.select_track('sub',window.video.media_info['sub'][0]['id'])
            window.video.seek_to(2)
            state['phase']=1
        elif phase==1 and abs((engine.time_pos or 0)-2)<.2 and text_value(engine.sub_text):
            state['small']=glyph_width()
            window.adjust_subtitle_size(50)
            state['phase']=2
        elif phase==2:
            large=glyph_width()
            assert large > state['small']*1.3
            assert engine.aid==state['audio'] and engine.sub_visibility
            window.grab().save(str(root/'runtime/subtitle-size-ui.png'))
            window.video.select_track('sub',window.video.media_info['sub'][1]['id'])
            state['phase']=3
        elif phase==3:
            assert not text_value(engine.sub_text), 'second cue should start at 5s'
            window.video.seek_to(6);state['phase']=4
        elif phase==4 and text_value(engine.sub_text)=='Second subtitle track':
            assert engine.aid==state['audio']
            assert glyph_width()>0
            print('Subtitle smoke: PASS (2 tracks, visible pixels, 150% increases width, future cue waits, audio unchanged)')
            window.close();app.quit();return
        if state['attempts']>80:raise AssertionError('timeout')
        QTimer.singleShot(300,check)
    except Exception as exc:
        print('Subtitle smoke: FAIL',type(exc).__name__,'phase',state['phase'])
        window.close();app.exit(1)
QTimer.singleShot(300,start)
raise SystemExit(app.exec())
