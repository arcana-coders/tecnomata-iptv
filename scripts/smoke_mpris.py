"""Native fictitious movie/episode and playerctl; never reads provider metadata."""
import os
import subprocess
import sys
import threading
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from tecnomata_iptv.app import Window, configure_appearance
root = Path(__file__).resolve().parents[1]
app = QApplication(sys.argv[:1]); configure_appearance(app)
name = f'tecnomata_iptv.instance{os.getpid()}'
events = []
follower = subprocess.Popen(['playerctl','-p',name,'metadata','--format','{{title}}\t{{status}}','-F'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
def listen():
    for line in follower.stdout: events.append(line.rstrip('\n'))
threading.Thread(target=listen,daemon=True).start()
window = Window(demo=True,demo_files=[root/'runtime/seek-demo.mp4'],restore=False,mpris_enabled=True)
window.show()
state = {'phase':0,'attempts':0}

def command(*args):
    result = subprocess.run(['playerctl','-p',name,*args],capture_output=True,text=True,timeout=3)
    assert result.returncode == 0, 'playerctl command failed'
    return result.stdout.strip()

def start():
    window.section('vod'); window.activate(window.items.item(0))
    QTimer.singleShot(100,check)

def check():
    try:
        state['attempts'] += 1
        phase = state['phase']
        if phase == 0 and window.mpris.available and window.video.diagnostic.get('state') == 'playing' and 'Película de prueba\tPlaying' in events:
            assert command('metadata','--format','{{title}}') == 'Película de prueba'
            assert command('status') == 'Playing'
            assert window.mpris.latest['Metadata']['mpris:length'].value > 0
            assert 'xesam:url' not in window.mpris.latest['Metadata']
            command('pause'); state['phase'] = 1
        elif phase == 1 and window.playback_status == 'Paused':
            assert window.video.engine.pause and command('status') == 'Paused'
            command('play'); state['phase'] = 2
        elif phase == 2 and window.playback_status == 'Playing':
            command('volume','0.42'); state['phase'] = 3
        elif phase == 3 and window.volume.value() == 42:
            assert window.video.engine.volume == 42
            window.section('series'); window.activate(window.items.item(0)); window.activate(window.items.item(0))
            state['phase'] = 4
        elif phase == 4 and window.video.diagnostic.get('state') == 'playing' and 'T1 · E1 · Episodio de prueba\tPlaying' in events:
            assert command('metadata','--format','{{title}}') == 'T1 · E1 · Episodio de prueba'
            command('stop'); state['phase'] = 5
        elif phase == 5 and window.video.pending_url is None:
            assert command('status') == 'Stopped' and window.mpris.latest['Metadata'] == {}
            window.close()
            assert not window.mpris.thread.is_alive()
            follower.terminate(); follower.wait(timeout=2)
            print('MPRIS smoke: PASS (movie/episode titles, pause/play/volume/stop via playerctl, no URL, service closed)')
            app.quit(); return
        if state['attempts'] > 100: raise AssertionError('timeout')
        QTimer.singleShot(100,check)
    except Exception as exc:
        print('MPRIS smoke: FAIL',type(exc).__name__, 'phase',state['phase'])
        follower.terminate(); follower.wait(timeout=2)
        window.close();app.exit(1)
QTimer.singleShot(300,start)
raise SystemExit(app.exec())
