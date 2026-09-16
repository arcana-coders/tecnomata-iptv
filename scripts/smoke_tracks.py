"""Real libmpv track selection using the synthetic runtime/tracks-demo.mkv."""
import sys
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from tecnomata_iptv.app import Window, configure_appearance

root = Path(__file__).resolve().parents[1]
app = QApplication(sys.argv[:1])
configure_appearance(app)
window = Window(demo=True, demo_files=[root / 'runtime/tracks-demo.mkv'], restore=False)
window.show()
failures = []
window.video.failed.connect(failures.append)
steps = {'count': 0}


def check():
    try:
        steps['count'] += 1
        info = window.video.media_info
        if not info.get('audio') and steps['count'] < 40:
            QTimer.singleShot(100, check)
            return
        assert not failures, 'Playback failed'
        assert info['width'] == 640 and info['height'] == 360
        assert info['fps'] == 25
        assert len(info['audio']) == 2 and len(info['sub']) == 1
        assert window.audio_tracks.count() == 2
        assert window.subtitle_tracks.count() == 2
        audio_id = info['audio'][1]['id']
        sub_id = info['sub'][0]['id']
        window.audio_tracks.setCurrentIndex(1)
        window.audio_tracks.activated.emit(1)
        window.subtitle_tracks.setCurrentIndex(1)
        window.subtitle_tracks.activated.emit(1)
        assert window.video.engine.aid == audio_id
        assert window.video.engine.sid == sub_id
        QTimer.singleShot(400, finish)
    except Exception:
        print('Tracks smoke: FAIL')
        window.close()
        app.exit(1)


def finish():
    try:
        assert window.video.frames > 10
        window.grab().save(str(root / 'runtime/tracks-ui.png'))
        window.subtitle_tracks.setCurrentIndex(0)
        window.subtitle_tracks.activated.emit(0)
        assert window.video.engine.sid is False or window.video.engine.sid == 'no'
        window.video.stop()
        assert not window.audio_tracks.isEnabled() and not window.subtitle_tracks.isEnabled()
        assert window.quality.text() == 'Sin reproducción'
        print('Tracks smoke: PASS (640x360, 25fps, two audio tracks, subtitle on/off, stop clears)')
        window.close()
        app.quit()
    except Exception:
        print('Tracks smoke finish: FAIL')
        window.close()
        app.exit(1)


QTimer.singleShot(300, lambda: window.activate(window.items.item(0)))
QTimer.singleShot(700, check)
raise SystemExit(app.exec())
