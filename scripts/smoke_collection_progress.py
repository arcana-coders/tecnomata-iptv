"""Native collection buttons: resume/restart, series favorite, narrow themed list."""
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from PySide6.QtCore import QTimer, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from tecnomata_iptv.app import Window,configure_appearance
from tecnomata_iptv.library import LibraryStore
from tecnomata_iptv.collection_row import CollectionRow
from tecnomata_iptv.themes import THEMES

root=Path(__file__).resolve().parents[1]
app=QApplication(sys.argv[:1]); configure_appearance(app)
folder=TemporaryDirectory(); db=LibraryStore(Path(folder.name)/'library.sqlite3')
for i,position in ((1,6),(2,10),(3,15)):
    row={'stream_id':i,'name':f'Película ficticia {i} — título largo para probar la lista','container_extension':'mkv'}
    db.played('demo','vod',row); db.toggle('demo','vod',row)
    db.save_progress('demo','vod',row,position=position,duration=15,audio={'id':2},subtitle={'id':2},subtitle_size=150,completed=i==3)
episode={'stream_id':1,'name':'T1 · E2 · Episodio ficticio','container_extension':'mkv'}
db.played('demo','episode',episode,'10','Serie ficticia')
db.save_progress('demo','episode',episode,'10',position=4,duration=15,audio={'id':1},subtitle='no',subtitle_size=90)
db.toggle('demo','series',{'series_id':10,'name':'Serie ficticia'})
window=Window(demo=True,demo_files=[root/'runtime/sub-size-demo.mkv'],restore=False,library_store=db)
window.resize(920,690); window.show()
state={'phase':0,'attempts':0}

def find(kind,identity):
    for i in range(window.items.count()):
        item=window.items.item(i); row=item.data(Qt.ItemDataRole.UserRole)
        if row['_kind']==kind and str(row.get('stream_id',row.get('series_id')))==str(identity):
            return window.items.itemWidget(item)
    raise AssertionError('missing fixture')

def click(button):
    QTest.mouseClick(button,Qt.MouseButton.LeftButton)

def start():
    window.show_collection('recent'); window.splitter.setSizes([325,0,560]); app.processEvents()
    for key in THEMES:
        window.theme_selector.setCurrentIndex(window.theme_selector.findData(key)); app.processEvents()
        for i in range(window.items.count()):
            widget=window.items.itemWidget(window.items.item(i))
            if isinstance(widget,CollectionRow):
                assert widget.restart_button.geometry().right() <= widget.width()
                assert widget.restart_button.geometry().bottom() < widget.height(), (key,widget.height(),widget.restart_button.geometry())
                assert widget.continue_button.width() >= widget.continue_button.fontMetrics().horizontalAdvance(widget.continue_button.text())+8
                assert widget.restart_button.width() >= widget.restart_button.fontMetrics().horizontalAdvance(widget.restart_button.text())+8, (key,widget.width(),widget.restart_button.width(),widget.restart_button.fontMetrics().horizontalAdvance(widget.restart_button.text()))
        window.grab().save(str(root/f'runtime/{key}-collection-progress.png'))
    click(find('vod',1).continue_button); QTimer.singleShot(100,check)

def check():
    try:
        state['attempts']+=1
        engine=window.video.engine
        if window.video.media_ready and not window.pending_resume and window.resume_target is None:
            engine.pause=True
            position=engine.time_pos or 0
            if state['phase']==0 and abs(position-6)<.5:
                assert engine.aid==2 and engine.sid==2 and abs(engine.sub_scale-1.5)<.01
                click(find('vod',1).restart_button); state['phase']=1
            elif state['phase']==1 and position<.5:
                assert engine.aid==2 and engine.sid==2 and abs(engine.sub_scale-1.5)<.01
                window.show_collection('favorites'); app.processEvents()
                for i in range(window.items.count()):
                    widget=window.items.itemWidget(window.items.item(i))
                    if isinstance(widget,CollectionRow):
                        assert widget.restart_button.geometry().bottom() < widget.height(), (widget.height(),widget.restart_button.geometry())
                window.grab().save(str(root/'runtime/favorite-series-progress.png'))
                assert find('series',10).progress_bar.value() == round(1000*4/15)
                click(find('series',10).continue_button); state['phase']=2
            elif state['phase']==2 and abs(position-4)<.5:
                assert engine.aid==1 and engine.sid is False and abs(engine.sub_scale-.9)<.01
                assert window.collection_view=='favorites' and window.progress_context[3]=='10'
                print('Collection progress smoke: PASS (four themes, narrow list, real resume/restart clicks, tracks kept, series favorite resumes episode)')
                window.close(); app.quit(); return
        if state['attempts']>100: raise AssertionError('timeout')
        QTimer.singleShot(100,check)
    except Exception as exc:
        print('Collection progress smoke: FAIL',type(exc).__name__,'phase',state['phase'])
        window.close(); app.exit(1)
def safe_start():
    try: start()
    except Exception as exc:
        print("Collection progress smoke: FAIL",type(exc).__name__,str(exc)); window.close(); app.exit(1)
QTimer.singleShot(300,safe_start)
result=app.exec(); folder.cleanup(); raise SystemExit(result)
