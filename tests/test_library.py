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
