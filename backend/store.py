"""SQLite record store and immutable, content-addressed graph revisions."""
from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

KINDS = ('companies', 'instruments', 'sources', 'relationships', 'claims', 'projects', 'participations', 'frontier', 'batches', 'coverage')


def now():
    return datetime.now(timezone.utc).isoformat()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def empty_snapshot():
    return {kind: [] for kind in KINDS} | {'meta': {}}


class Store:
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.data_dir / 'graph.sqlite3'
        with self.connection() as conn:
            conn.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS records(kind TEXT NOT NULL,id TEXT NOT NULL,payload TEXT NOT NULL,PRIMARY KEY(kind,id));
                CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS revisions(revision INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,description TEXT NOT NULL,snapshot_hash TEXT NOT NULL,batch_id TEXT,snapshot TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS proposals(id TEXT PRIMARY KEY,batch_id TEXT NOT NULL,base_revision INTEGER NOT NULL,content_hash TEXT NOT NULL,payload TEXT NOT NULL,result TEXT NOT NULL,created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS published_batches(batch_id TEXT PRIMARY KEY,content_hash TEXT NOT NULL,revision INTEGER NOT NULL);
            ''')

    @contextmanager
    def connection(self):
        conn = sqlite3.connect(self.path, timeout=20)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys=ON')
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def revision(self, conn=None):
        if conn is None:
            with self.connection() as own:
                return self.revision(own)
        return conn.execute('SELECT COALESCE(MAX(revision),0) FROM revisions').fetchone()[0]

    def snapshot(self, revision=None, conn=None):
        if conn is None:
            with self.connection() as own:
                return self.snapshot(revision, own)
        if revision is not None:
            row = conn.execute('SELECT snapshot FROM revisions WHERE revision=?', (revision,)).fetchone()
            if row is None:
                raise KeyError(revision)
            return json.loads(row[0])
        result = empty_snapshot()
        for row in conn.execute('SELECT kind,payload FROM records ORDER BY kind,id'):
            result[row['kind']].append(json.loads(row['payload']))
        row = conn.execute("SELECT value FROM metadata WHERE key='meta'").fetchone()
        if row:
            result['meta'] = json.loads(row[0])
        return result

    def commit_snapshot(self, snapshot, description, batch_id=None, conn=None):
        if conn is None:
            with self.connection() as own:
                own.execute('BEGIN IMMEDIATE')
                return self.commit_snapshot(snapshot, description, batch_id, own)
        ordered = copy.deepcopy(snapshot)
        for kind in KINDS:
            ordered[kind] = sorted(ordered.get(kind, []), key=lambda value: value['id'])
        encoded = canonical(ordered)
        checksum = hashlib.sha256(encoded.encode('utf-8')).hexdigest()
        conn.execute('DELETE FROM records')
        conn.executemany('INSERT INTO records(kind,id,payload) VALUES(?,?,?)', [(kind, row['id'], canonical(row)) for kind in KINDS for row in ordered[kind]])
        conn.execute("INSERT OR REPLACE INTO metadata(key,value) VALUES('meta',?)", (canonical(ordered.get('meta', {})),))
        cursor = conn.execute('INSERT INTO revisions(created_at,description,snapshot_hash,batch_id,snapshot) VALUES(?,?,?,?,?)', (now(), description, checksum, batch_id, encoded))
        return {'revision': cursor.lastrowid, 'snapshot_hash': checksum}

    def get(self, kind, identifier):
        with self.connection() as conn:
            row = conn.execute('SELECT payload FROM records WHERE kind=? AND id=?', (kind, identifier)).fetchone()
            return json.loads(row[0]) if row else None

    def revisions(self):
        with self.connection() as conn:
            return [dict(row) for row in conn.execute('SELECT revision,created_at,description,snapshot_hash,batch_id FROM revisions ORDER BY revision DESC')]
