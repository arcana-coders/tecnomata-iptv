from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from tecnomata_iptv.app import Window
from tecnomata_iptv.library import LibraryStore
from tecnomata_iptv.collection_row import CollectionRow


def seed(db):
    movie = {'stream_id':1,'name':'Synthetic movie','container_extension':'mkv'}
    episode = {'stream_id':2,'name':'T1 E2 Synthetic episode','container_extension':'mkv'}
    series = {'series_id':10,'name':'Synthetic series'}
    db.played('demo','vod',movie); db.toggle('demo','vod',movie)
    db.save_progress('demo','vod',movie,position=30,duration=120,audio={'id':2},subtitle='no',subtitle_size=150)
    db.played('demo','episode',episode,'10','Synthetic series')
    db.save_progress('demo','episode',episode,'10',position=50,duration=100)
    db.toggle('demo','series',series)
    db.played('demo','live',{'stream_id':3,'name':'Synthetic live'})
    return movie,episode,series


def card(window,kind):
    return next((window.items.item(i),window.items.itemWidget(window.items.item(i))) for i in range(window.items.count())
                if window.items.item(i).data(Qt.ItemDataRole.UserRole)['_kind']==kind)


def test_recent_and_favorite_progress_buttons_use_their_content(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = LibraryStore(tmp_path/'library.sqlite3'); movie,episode,series = seed(db)
    window = Window(demo=True,demo_files=['synthetic.mkv'],restore=False,library_store=db)
    window.show(); window.show_collection('recent'); app.processEvents()
    item,widget = card(window,'vod')
    assert isinstance(widget,CollectionRow)
    assert widget.progress_bar.value() == 250
    assert '0:30 / 2:00' in widget.status.full_text
    assert card(window,'episode')[1].progress_bar.value() == 500
    assert card(window,'live')[1] is None
    QTest.mouseClick(widget.continue_button,Qt.MouseButton.LeftButton)
    assert window.pending_resume['position'] == 30 and window.progress_context[2]['stream_id']=='1'
    QTest.mouseClick(widget.restart_button,Qt.MouseButton.LeftButton)
    assert window.pending_resume['position'] == 0
    assert window.pending_resume['audio']['id'] == 2 and window.pending_resume['subtitle']=='no'
    assert db.progress('demo','vod',movie)['position'] == 30  # Do not erase before successful loading.
    window.show_collection('favorites'); app.processEvents()
    item,widget = card(window,'series')
    assert widget.progress_bar.value() == 500 and 'T1 E2' in widget.status.full_text
    QTest.mouseClick(widget.continue_button,Qt.MouseButton.LeftButton)
    assert window.progress_context[1] == 'episode' and window.progress_context[3] == '10'
    assert window.pending_resume['position'] == 50
    assert item.data(Qt.ItemDataRole.UserRole)['_kind']=='series'
    assert window.collection_view == 'favorites'
    window.close()


def test_completed_and_unwatched_cards_and_star_removal(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = LibraryStore(tmp_path/'library.sqlite3')
    for i in (1,2): db.toggle('demo','vod',{'stream_id':i,'name':f'Movie {i}'})
    db.save_progress('demo','vod',{'stream_id':1},position=100,duration=100,completed=True)
    window = Window(demo=True,restore=False,library_store=db)
    window.show(); window.show_collection('favorites'); app.processEvents()
    first = window.items.itemWidget(window.items.item(0))
    second = window.items.itemWidget(window.items.item(1))
    assert first.progress_bar.value()==1000 and first.status.full_text=='Visto · 100%'
    assert not first.continue_button.isEnabled() and first.restart_button.isEnabled()
    assert second.progress_bar.value()==0 and second.status.full_text=='Sin iniciar'
    assert not second.continue_button.isEnabled() and second.restart_button.isEnabled()
    QTest.mouseClick(first.star,Qt.MouseButton.LeftButton)
    assert window.items.count()==1 and window.video.pending_url is None
    window.close()


def test_series_last_episode_metadata_survives_recent_pruning_and_account_isolation(tmp_path):
    db = LibraryStore(tmp_path/'library.sqlite3'); _,episode,series = seed(db)
    for i in range(110): db.played('demo','vod',{'stream_id':100+i})
    assert not any(row['_kind']=='episode' for row in db.rows('demo','recent'))
    row,saved = db.latest_episode('demo',series)
    assert row['name']==episode['name'] and row['container_extension']=='mkv'
    assert saved['position']==50
    assert db.latest_episode('other',series) is None
    db.close()


def test_existing_checkpoint_schema_enriches_episode_metadata(tmp_path):
    path = tmp_path/'library.sqlite3'
    db = LibraryStore(path); _,episode,series = seed(db)
    db.db.execute('ALTER TABLE progress DROP COLUMN name')
    db.db.execute('ALTER TABLE progress DROP COLUMN extension')
    db.db.commit(); db.close()
    db = LibraryStore(path)
    row,saved = db.latest_episode('demo',series)
    assert row['name']==episode['name'] and row['container_extension']=='mkv'
    assert saved['position']==50
    db.close()
