"""Account-scoped favorites and recent successful plays, without account secrets."""
import hashlib
import json
import math
import os
import sqlite3
from pathlib import Path
import time


class LibraryError(Exception):
    pass


def account_scope(account):
    # Password rotation preserves the library; no account fields go into SQLite.
    return hashlib.sha256((account.server + '\0' + account.username).encode()).hexdigest()


class LibraryStore:
    def __init__(self, path=None):
        if path is None:
            root = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'tecnomata-iptv'
            path = root / 'library.sqlite3'
        try:
            if str(path) != ':memory:':
                path = Path(path)
                path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                # Create with restricted permissions before SQLite opens the file.
                fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
                os.close(fd)
                path.chmod(0o600)
            self.db = sqlite3.connect(str(path))
            self.db.row_factory = sqlite3.Row
            self.db.execute('''CREATE TABLE IF NOT EXISTS entries (
                scope TEXT NOT NULL, kind TEXT NOT NULL, id TEXT NOT NULL,
                name TEXT NOT NULL, category TEXT, extension TEXT,
                parent TEXT NOT NULL DEFAULT '', series_name TEXT NOT NULL DEFAULT '',
                favorite INTEGER NOT NULL DEFAULT 0, played REAL,
                PRIMARY KEY (scope, kind, id, parent))''')
            self.db.execute('''CREATE TABLE IF NOT EXISTS progress (
                scope TEXT NOT NULL, kind TEXT NOT NULL, id TEXT NOT NULL, parent TEXT NOT NULL,
                position REAL NOT NULL, duration REAL NOT NULL, audio TEXT, subtitle TEXT,
                subtitle_size INTEGER NOT NULL, completed INTEGER NOT NULL DEFAULT 0,
                updated REAL NOT NULL, PRIMARY KEY(scope,kind,id,parent))''')
            self.db.commit()
        except (OSError, sqlite3.Error):
            raise LibraryError('No se pudo abrir la biblioteca local.') from None

    def _entry(self, scope, kind, row, parent='', series_name=''):
        key = 'series_id' if kind == 'series' else 'stream_id'
        identity = str(row.get(key, ''))
        if kind not in ('live', 'vod', 'series', 'episode') or not identity.isdigit():
            raise LibraryError('Este contenido no tiene un identificador válido para guardarlo.')
        return (scope, kind, identity, str(parent or ''), str(row.get('name', 'Sin nombre')),
                str(row.get('category_id', '')), str(row.get('container_extension', '')),
                str(series_name or ''))

    def _upsert(self, entry):
        self.db.execute('''INSERT INTO entries(scope,kind,id,parent,name,category,extension,series_name)
            VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(scope,kind,id,parent) DO UPDATE SET
            name=excluded.name,category=excluded.category,extension=excluded.extension,
            series_name=excluded.series_name''', entry)

    def is_favorite(self, scope, kind, row, parent=''):
        entry = self._entry(scope, kind, row, parent)
        try:
            result = self.db.execute('SELECT favorite FROM entries WHERE scope=? AND kind=? AND id=? AND parent=?', entry[:4]).fetchone()
            return bool(result and result['favorite'])
        except sqlite3.Error:
            raise LibraryError('No se pudo leer el favorito.') from None

    def toggle(self, scope, kind, row, parent='', series_name=''):
        try:
            entry = self._entry(scope, kind, row, parent, series_name)
            with self.db:
                self._upsert(entry)
                self.db.execute('UPDATE entries SET favorite=1-favorite WHERE scope=? AND kind=? AND id=? AND parent=?', entry[:4])
            return self.is_favorite(scope, kind, row, parent)
        except sqlite3.Error:
            raise LibraryError('No se pudo guardar el favorito.') from None

    def played(self, scope, kind, row, parent='', series_name=''):
        try:
            entry = self._entry(scope, kind, row, parent, series_name)
            with self.db:
                self._upsert(entry)
                self.db.execute('UPDATE entries SET played=? WHERE scope=? AND kind=? AND id=? AND parent=?', (time.time(), *entry[:4]))
                self.db.execute('''DELETE FROM entries WHERE scope=? AND favorite=0 AND played IS NOT NULL
                    AND rowid NOT IN (SELECT rowid FROM entries WHERE scope=? AND played IS NOT NULL
                    ORDER BY played DESC LIMIT 100)''', (scope, scope))
        except sqlite3.Error:
            raise LibraryError('No se pudo guardar el historial.') from None

    def rows(self, scope, view):
        try:
            if view == 'favorites':
                entries = self.db.execute('SELECT * FROM entries WHERE scope=? AND favorite=1 ORDER BY name COLLATE NOCASE', (scope,)).fetchall()
            else:
                entries = self.db.execute('SELECT * FROM entries WHERE scope=? AND played IS NOT NULL ORDER BY played DESC LIMIT 100', (scope,)).fetchall()
            return [{('series_id' if item['kind'] == 'series' else 'stream_id'): item['id'],
                'name': item['name'], 'category_id': item['category'],
                'container_extension': item['extension'] or None,
                '_kind': item['kind'], '_parent': item['parent'],
                '_series_name': item['series_name'], '_played': item['played']} for item in entries]
        except sqlite3.Error:
            raise LibraryError('No se pudo leer la biblioteca local.') from None

    def progress(self, scope, kind, row, parent=''):
        if kind not in ('vod','episode'):
            return None
        entry = self._entry(scope, kind, row, parent)
        try:
            item = self.db.execute('SELECT * FROM progress WHERE scope=? AND kind=? AND id=? AND parent=?',entry[:4]).fetchone()
            if not item:
                return None
            result = dict(item)
            for key in ('audio','subtitle'):
                result[key] = json.loads(result[key]) if result[key] else None
            return result
        except (sqlite3.Error, ValueError):
            raise LibraryError('No se pudo leer el punto de reproducción.') from None

    def save_progress(self, scope, kind, row, parent='', *, position, duration, audio=None,
                      subtitle=None, subtitle_size=100, completed=False):
        if kind not in ('vod','episode'):
            return
        entry = self._entry(scope, kind, row, parent)
        def clean(choice):
            if choice == 'no':
                return json.dumps('no')
            if not isinstance(choice,dict):
                return None
            return json.dumps({key:choice[key] for key in ('id','lang','codec','title') if key in choice},ensure_ascii=False)
        try:
            position, duration = float(position), float(duration)
            if not math.isfinite(position) or not math.isfinite(duration) or position < 0 or duration <= 0:
                return
            values = (*entry[:4], 0 if completed else min(position,duration), duration,
                      clean(audio),clean(subtitle),max(50,min(250,int(subtitle_size))),int(completed),time.time())
            with self.db:
                self.db.execute('''INSERT INTO progress VALUES (?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(scope,kind,id,parent) DO UPDATE SET position=excluded.position,
                    duration=excluded.duration,audio=excluded.audio,subtitle=excluded.subtitle,
                    subtitle_size=excluded.subtitle_size,completed=excluded.completed,updated=excluded.updated''',values)
        except sqlite3.Error:
            raise LibraryError('No se pudo guardar el punto de reproducción.') from None

    def close(self):
        self.db.close()
