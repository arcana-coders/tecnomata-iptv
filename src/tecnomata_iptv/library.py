"""Account-scoped favorites and recent successful plays, without account secrets."""
import hashlib
import json
import math
import os
import sqlite3
import uuid
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
            self.db.execute('''CREATE TABLE IF NOT EXISTS lists (
                scope TEXT NOT NULL, list_id TEXT NOT NULL, name TEXT NOT NULL,
                created REAL NOT NULL, PRIMARY KEY (scope, list_id))''')
            self.db.execute('''CREATE TABLE IF NOT EXISTS list_members (
                scope TEXT NOT NULL, list_id TEXT NOT NULL, kind TEXT NOT NULL, id TEXT NOT NULL,
                parent TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (scope, list_id, kind, id, parent))''')
            self.db.execute('''CREATE TABLE IF NOT EXISTS quality (
                scope TEXT NOT NULL, kind TEXT NOT NULL, id TEXT NOT NULL,
                tier TEXT, width INTEGER, height INTEGER, scanned REAL NOT NULL,
                PRIMARY KEY (scope, kind, id))''')
            columns = {column['name'] for column in self.db.execute('PRAGMA table_info(progress)')}
            for name in ('name','extension'):
                if name not in columns:
                    self.db.execute(f"ALTER TABLE progress ADD COLUMN {name} TEXT NOT NULL DEFAULT ''")
            # Enrich checkpoints created before collection cards stored episode metadata.
            self.db.execute("""UPDATE progress SET name=COALESCE((SELECT name FROM entries
                WHERE entries.scope=progress.scope AND entries.kind=progress.kind
                AND entries.id=progress.id AND entries.parent=progress.parent),'') WHERE name=''""")
            self.db.execute("""UPDATE progress SET extension=COALESCE((SELECT extension FROM entries
                WHERE entries.scope=progress.scope AND entries.kind=progress.kind
                AND entries.id=progress.id AND entries.parent=progress.parent),'') WHERE extension=''""")
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

    def _row_dict(self, item):
        return {
            ('series_id' if item['kind'] == 'series' else 'stream_id'): item['id'],
            'name': item['name'],
            'category_id': item['category'],
            'container_extension': item['extension'] or None,
            '_kind': item['kind'],
            '_parent': item['parent'],
            '_series_name': item['series_name'],
            '_played': item['played'] if 'played' in item.keys() else None,
        }

    def rows(self, scope, view):
        try:
            if view == 'favorites':
                entries = self.db.execute('SELECT * FROM entries WHERE scope=? AND favorite=1 ORDER BY name COLLATE NOCASE', (scope,)).fetchall()
            else:
                entries = self.db.execute('SELECT * FROM entries WHERE scope=? AND played IS NOT NULL ORDER BY played DESC LIMIT 100', (scope,)).fetchall()
            return [self._row_dict(item) for item in entries]
        except sqlite3.Error:
            raise LibraryError('No se pudo leer la biblioteca local.') from None

    def create_list(self, scope, name):
        name = str(name).strip()
        if not name:
            raise LibraryError('El nombre de la lista no puede estar vacío.')
        list_id = uuid.uuid4().hex
        try:
            with self.db:
                self.db.execute('INSERT INTO lists(scope,list_id,name,created) VALUES (?,?,?,?)',
                    (scope, list_id, name, time.time()))
            return list_id
        except sqlite3.Error:
            raise LibraryError('No se pudo crear la lista.') from None

    def rename_list(self, scope, list_id, name):
        name = str(name).strip()
        if not name:
            raise LibraryError('El nombre de la lista no puede estar vacío.')
        try:
            with self.db:
                self.db.execute('UPDATE lists SET name=? WHERE scope=? AND list_id=?', (name, scope, list_id))
        except sqlite3.Error:
            raise LibraryError('No se pudo renombrar la lista.') from None

    def delete_list(self, scope, list_id):
        try:
            with self.db:
                self.db.execute('DELETE FROM list_members WHERE scope=? AND list_id=?', (scope, list_id))
                self.db.execute('DELETE FROM lists WHERE scope=? AND list_id=?', (scope, list_id))
        except sqlite3.Error:
            raise LibraryError('No se pudo eliminar la lista.') from None

    def lists(self, scope):
        try:
            entries = self.db.execute('''SELECT lists.list_id AS list_id, lists.name AS name,
                COUNT(list_members.id) AS count FROM lists LEFT JOIN list_members
                ON lists.scope=list_members.scope AND lists.list_id=list_members.list_id
                WHERE lists.scope=? GROUP BY lists.list_id ORDER BY lists.name COLLATE NOCASE''', (scope,)).fetchall()
            return [{'list_id': item['list_id'], 'name': item['name'], 'count': item['count']} for item in entries]
        except sqlite3.Error:
            raise LibraryError('No se pudieron leer las listas.') from None

    def list_by_name(self, scope, name):
        try:
            item = self.db.execute('SELECT list_id FROM lists WHERE scope=? AND name=?', (scope, name)).fetchone()
            return item['list_id'] if item else None
        except sqlite3.Error:
            raise LibraryError('No se pudo buscar la lista.') from None

    def list_membership(self, scope, kind, row, parent=''):
        entry = self._entry(scope, kind, row, parent)
        try:
            entries = self.db.execute('SELECT list_id FROM list_members WHERE scope=? AND kind=? AND id=? AND parent=?', entry[:4]).fetchall()
            return {item['list_id'] for item in entries}
        except sqlite3.Error:
            raise LibraryError('No se pudo leer la pertenencia a listas.') from None

    def set_list_membership(self, scope, list_id, kind, row, parent='', member=True, series_name=''):
        entry = self._entry(scope, kind, row, parent, series_name)
        try:
            with self.db:
                self._upsert(entry)
                if member:
                    self.db.execute('''INSERT OR IGNORE INTO list_members(scope,list_id,kind,id,parent)
                        VALUES (?,?,?,?,?)''', (scope, list_id, entry[1], entry[2], entry[3]))
                else:
                    self.db.execute('''DELETE FROM list_members WHERE scope=? AND list_id=?
                        AND kind=? AND id=? AND parent=?''', (scope, list_id, entry[1], entry[2], entry[3]))
        except sqlite3.Error:
            raise LibraryError('No se pudo actualizar la lista.') from None

    def replace_list_members(self, scope, list_id, members):
        """members: iterable of (kind, row, parent) that becomes the exact list contents."""
        try:
            with self.db:
                self.db.execute('DELETE FROM list_members WHERE scope=? AND list_id=?', (scope, list_id))
                for kind, row, parent in members:
                    entry = self._entry(scope, kind, row, parent)
                    self._upsert(entry)
                    self.db.execute('''INSERT OR IGNORE INTO list_members(scope,list_id,kind,id,parent)
                        VALUES (?,?,?,?,?)''', (scope, list_id, entry[1], entry[2], entry[3]))
        except sqlite3.Error:
            raise LibraryError('No se pudo actualizar la lista generada.') from None

    def list_rows(self, scope, list_id):
        try:
            entries = self.db.execute('''SELECT entries.* FROM entries JOIN list_members
                ON entries.scope=list_members.scope AND entries.kind=list_members.kind
                AND entries.id=list_members.id AND entries.parent=list_members.parent
                WHERE entries.scope=? AND list_members.list_id=?
                ORDER BY entries.name COLLATE NOCASE''', (scope, list_id)).fetchall()
            return [self._row_dict(item) for item in entries]
        except sqlite3.Error:
            raise LibraryError('No se pudo leer la lista.') from None

    def list_membership_map(self, scope, kind):
        """One query for the whole visible list, instead of one per row on every keystroke."""
        try:
            entries = self.db.execute('SELECT id, list_id FROM list_members WHERE scope=? AND kind=?', (scope, kind)).fetchall()
            result = {}
            for item in entries:
                result.setdefault(item['id'], set()).add(item['list_id'])
            return result
        except sqlite3.Error:
            raise LibraryError('No se pudo leer la pertenencia a listas.') from None

    def quality_map(self, scope, kind):
        try:
            entries = self.db.execute('SELECT id, tier FROM quality WHERE scope=? AND kind=?', (scope, kind)).fetchall()
            return {item['id']: item['tier'] for item in entries if item['tier']}
        except sqlite3.Error:
            raise LibraryError('No se pudo leer la calidad.') from None

    def save_quality(self, scope, kind, row, tier, width=None, height=None):
        entry = self._entry(scope, kind, row)
        try:
            with self.db:
                self._upsert(entry)
                self.db.execute('''INSERT INTO quality(scope,kind,id,tier,width,height,scanned)
                    VALUES (?,?,?,?,?,?,?) ON CONFLICT(scope,kind,id) DO UPDATE SET
                    tier=excluded.tier,width=excluded.width,height=excluded.height,scanned=excluded.scanned''',
                    (scope, entry[1], entry[2], tier, width, height, time.time()))
        except sqlite3.Error:
            raise LibraryError('No se pudo guardar la calidad detectada.') from None

    def quality_of(self, scope, kind, row):
        entry = self._entry(scope, kind, row)
        try:
            item = self.db.execute('SELECT tier FROM quality WHERE scope=? AND kind=? AND id=?',
                (scope, entry[1], entry[2])).fetchone()
            return item['tier'] if item else None
        except sqlite3.Error:
            raise LibraryError('No se pudo leer la calidad.') from None

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

    def latest_episode(self, scope, series):
        """Last watched episode of a series, independent of recent-history pruning."""
        entry = self._entry(scope,'series',series)
        try:
            item = self.db.execute("""SELECT * FROM progress WHERE scope=? AND kind='episode'
                AND parent=? ORDER BY updated DESC, id DESC LIMIT 1""",(scope,entry[2])).fetchone()
            if not item:
                return None
            row = {'stream_id':item['id'], 'name':item['name'] or 'Episodio',
                   'container_extension':item['extension'] or None, '_kind':'episode',
                   '_parent':item['parent'], '_series_name':entry[4]}
            return row, self.progress(scope,'episode',row,item['parent'])
        except sqlite3.Error:
            raise LibraryError('No se pudo leer el último episodio de esta serie.') from None

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
                      clean(audio),clean(subtitle),max(50,min(250,int(subtitle_size))),int(completed),time.time(),entry[4],entry[6])
            with self.db:
                self.db.execute('''INSERT INTO progress(scope,kind,id,parent,position,duration,audio,subtitle,subtitle_size,completed,updated,name,extension)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(scope,kind,id,parent) DO UPDATE SET position=excluded.position,
                    duration=excluded.duration,audio=excluded.audio,subtitle=excluded.subtitle,
                    subtitle_size=excluded.subtitle_size,completed=excluded.completed,updated=excluded.updated,name=excluded.name,extension=excluded.extension''',values)
        except sqlite3.Error:
            raise LibraryError('No se pudo guardar el punto de reproducción.') from None

    def close(self):
        self.db.close()
