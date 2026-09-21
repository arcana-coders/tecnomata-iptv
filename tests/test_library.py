import stat
import pytest
from tecnomata_iptv.library import LibraryStore, LibraryError, account_scope
from tecnomata_iptv.xtream import Account


def test_library_survives_reopen_and_scopes_accounts_without_credentials(tmp_path):
    path = tmp_path / 'data/library.sqlite3'
    account = Account('https://example.invalid', 'private-user', 'private-password')
    scope = account_scope(account)
    assert scope == account_scope(Account(account.server, account.username, 'rotated'))
    other = account_scope(Account(account.server, 'other-user', 'p'))
    store = LibraryStore(path)
    row = {'stream_id': 7, 'name': 'Canal A', 'container_extension': 'ts',
           'url': 'https://example.invalid/private-password', 'password': 'private-password'}
    assert store.toggle(scope, 'live', row)
    store.played(scope, 'live', row)
    store.close()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    payload = path.read_bytes()
    assert b'private-password' not in payload and b'private-user' not in payload
    assert b'https://example.invalid' not in payload
    store = LibraryStore(path)
    assert store.rows(other, 'favorites') == []
    assert store.rows(scope, 'favorites')[0]['stream_id'] == '7'
    assert store.rows(scope, 'recent')[0]['name'] == 'Canal A'
    assert not store.toggle(scope, 'live', row)
    assert store.rows(scope, 'favorites') == []
    assert len(store.rows(scope, 'recent')) == 1
    store.close()


def test_recent_order_dedup_limit_and_namespace(monkeypatch):
    store = LibraryStore(':memory:')
    clock = iter(range(1000))
    monkeypatch.setattr('tecnomata_iptv.library.time.time', lambda: next(clock))
    for i in range(110):
        store.played('a', 'live', {'stream_id': i, 'name': str(i)})
    recent = store.rows('a', 'recent')
    assert len(recent) == 100 and recent[0]['stream_id'] == '109'
    store.played('a', 'live', {'stream_id': 55, 'name': 'Renamed'})
    recent = store.rows('a', 'recent')
    assert recent[0]['name'] == 'Renamed'
    assert sum(row['stream_id'] == '55' for row in recent) == 1
    store.toggle('a', 'vod', {'stream_id': 55, 'name': 'Movie'})
    store.toggle('a', 'episode', {'stream_id': 55, 'name': 'Pilot'}, '999', 'Series')
    assert len(store.rows('a', 'favorites')) == 2
    assert store.rows('a', 'favorites')[1]['_parent'] == '999'
    store.close()


def test_old_favorites_are_not_pruned_and_bad_ids_are_rejected():
    store = LibraryStore(':memory:')
    row = {'stream_id': 1, 'name': 'Favorite'}
    store.toggle('a', 'live', row)
    store.played('a', 'live', row)
    for i in range(2, 115):
        store.played('a', 'live', {'stream_id': i, 'name': str(i)})
    assert store.rows('a', 'favorites')[0]['name'] == 'Favorite'
    with pytest.raises(LibraryError):
        store.toggle('a', 'vod', {'stream_id': 'https://invalid', 'name': 'bad'})
    store.close()


def test_custom_lists_create_rename_membership_and_delete_are_scoped():
    store = LibraryStore(':memory:')
    channel_a = {'stream_id': 1, 'name': 'HBO'}
    channel_b = {'stream_id': 2, 'name': 'HBO 2'}
    list_id = store.create_list('a', ' Deportes ')
    assert store.lists('a') == [{'list_id': list_id, 'name': 'Deportes', 'count': 0}]
    assert store.lists('b') == []
    store.set_list_membership('a', list_id, 'live', channel_a)
    store.set_list_membership('a', list_id, 'live', channel_b)
    assert store.lists('a')[0]['count'] == 2
    assert store.list_membership('a', 'live', channel_a) == {list_id}
    names = {row['name'] for row in store.list_rows('a', list_id)}
    assert names == {'HBO', 'HBO 2'}
    assert store.list_rows('b', list_id) == []
    store.set_list_membership('a', list_id, 'live', channel_a, member=False)
    assert len(store.list_rows('a', list_id)) == 1
    store.rename_list('a', list_id, 'Deportes MX')
    assert store.lists('a')[0]['name'] == 'Deportes MX'
    assert store.list_by_name('a', 'Deportes MX') == list_id
    with pytest.raises(LibraryError):
        store.create_list('a', '   ')
    store.delete_list('a', list_id)
    assert store.lists('a') == []
    assert store.list_rows('a', list_id) == []
    store.close()


def test_replace_list_members_regenerates_exact_contents():
    store = LibraryStore(':memory:')
    list_id = store.create_list('a', 'hbo · HD')
    channel_a = {'stream_id': 1, 'name': 'HBO'}
    channel_b = {'stream_id': 2, 'name': 'HBO 2'}
    store.replace_list_members('a', list_id, [('live', channel_a, '')])
    assert {row['name'] for row in store.list_rows('a', list_id)} == {'HBO'}
    store.replace_list_members('a', list_id, [('live', channel_b, '')])
    assert {row['name'] for row in store.list_rows('a', list_id)} == {'HBO 2'}
    store.close()


def test_membership_and_quality_maps_batch_lookups_for_the_visible_list():
    store = LibraryStore(':memory:')
    channel_a = {'stream_id': 1, 'name': 'HBO'}
    channel_b = {'stream_id': 2, 'name': 'HBO 2'}
    list_id = store.create_list('a', 'HBO HD')
    store.set_list_membership('a', list_id, 'live', channel_a)
    store.save_quality('a', 'live', channel_a, 'hd', 1280, 720)
    assert store.list_membership_map('a', 'live') == {'1': {list_id}}
    assert store.list_membership_map('b', 'live') == {}
    assert store.quality_map('a', 'live') == {'1': 'hd'}
    store.save_quality('a', 'live', channel_b, None, None, None)
    assert store.quality_map('a', 'live') == {'1': 'hd'}  # None tiers stay out of the map.
    store.close()


def test_quality_is_scoped_and_overwritten_on_rescan():
    store = LibraryStore(':memory:')
    channel = {'stream_id': 1, 'name': 'HBO'}
    assert store.quality_of('a', 'live', channel) is None
    store.save_quality('a', 'live', channel, 'hd', 1280, 720)
    assert store.quality_of('a', 'live', channel) == 'hd'
    assert store.quality_of('b', 'live', channel) is None
    store.save_quality('a', 'live', channel, 'fullhd', 1920, 1080)
    assert store.quality_of('a', 'live', channel) == 'fullhd'
    store.close()
