"""Native synthetic video seeks; never connects to provider or restores account."""
import sys
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from tecnomata_iptv.app import Window, configure_appearance
root = Path(__file__).resolve().parents[1]
app = QApplication(sys.argv[:1]); configure_appearance(app)
window = Window(demo=True, demo_files=[root/'runtime/seek-demo.mp4'], restore=False)
window.show(); phase = {'value':0,'attempts':0,'content':'vod'}

def start():
    window.section('vod'); window.activate(window.items.item(0))
    QTimer.singleShot(250, check)

def check():
    try:
        phase['attempts'] += 1
        position = window.video.engine.time_pos
        if phase['value'] == 0 and window.seek_duration > 0 and window.video.frames > 5:
            window.video.clicked.emit()
            assert window.timeline.isVisible() and window.seek_slider.isEnabled()
            window.video.engine.pause = True
            window.seek_fraction(600); phase['value'] = 1
        elif phase['value'] == 1 and position is not None and abs(position-12)<.3:
            window.seek_fraction(150); phase['value'] = 2
        elif phase['value'] == 2 and position is not None and abs(position-3)<.3:
            window.grab().save(str(root/'runtime/seek-controls.png'))
            window.stop_playback()
            assert window.timeline.isHidden() and window.video.pending_url is None
            if phase['content'] == 'vod':
                phase.update(value=0, attempts=0, content='series')
                window.section('series')
                window.activate(window.items.item(0))
                window.activate(window.items.item(0))
                assert window.playing_kind == 'series'
                QTimer.singleShot(250,check)
                return
            print('Seek smoke: PASS (movie + episode forward 12s, backward 3s, pause and stop reset)')
            window.close(); app.quit(); return
        if phase['attempts'] > 80:
            raise AssertionError('seek timeout')
        QTimer.singleShot(100, check)
    except Exception as exc:
        print('Seek smoke: FAIL', type(exc).__name__)
        window.close(); app.exit(1)
QTimer.singleShot(300,start)
raise SystemExit(app.exec())
