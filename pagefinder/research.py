"""Versioned local evidence store shared by both future retrieval strategies."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3

from .privacy import private_dir, outside_repo

SCHEMA_VERSION = 1
METHOD = 'pagefinder-local/1'
COMPLETENESS = ('unknown', 'partial', 'complete_for_request', 'bounded_export', 'unsupported')


def now():
    return datetime.now(timezone.utc).isoformat()


def stable_id(*parts):
    return hashlib.sha256(json.dumps(parts, ensure_ascii=False).encode()).hexdigest()


class Store:
    def __init__(self, folder: Path):
        self.folder = private_dir(folder)
        path = outside_repo(self.folder / 'research.sqlite3')
        self.db = sqlite3.connect(path, timeout=10)
        path.chmod(0o600)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        version = self.db.execute('PRAGMA user_version').fetchone()[0]
        if version > SCHEMA_VERSION:
            self.db.close()
            raise ValueError('Database is newer than this code; use a compatible version')
        if version == 0:
            # An unknown nonempty database is not a v0 migration input.
            tables = self.db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            if tables:
                self.db.close()
                raise ValueError('Unversioned nonempty database; refusing to guess a migration')
            self.db.executescript('''BEGIN IMMEDIATE;
                CREATE TABLE evidence (
                    id TEXT PRIMARY KEY, source_type TEXT NOT NULL, source_ref TEXT NOT NULL,
                    retrieved_at TEXT NOT NULL, observed_at TEXT, confidence REAL NOT NULL
                    CHECK(confidence BETWEEN 0 AND 1), visibility TEXT NOT NULL
                    CHECK(visibility IN ('public','private')), method TEXT NOT NULL,
                    completeness TEXT NOT NULL CHECK(completeness IN
                    ('unknown','partial','complete_for_request','bounded_export','unsupported')),
                    notes TEXT NOT NULL);
                CREATE TABLE entities (
                    id TEXT PRIMARY KEY, kind TEXT NOT NULL, native_id TEXT NOT NULL,
                    canonical_url TEXT NOT NULL, title TEXT NOT NULL, creator_id TEXT,
                    published_at TEXT, availability TEXT NOT NULL, visibility TEXT NOT NULL
                    CHECK(visibility IN ('public','private')), evidence_id TEXT NOT NULL REFERENCES evidence(id));
                CREATE TABLE titles (
                    entity_id TEXT REFERENCES entities(id), title TEXT NOT NULL,
                    evidence_id TEXT REFERENCES evidence(id), PRIMARY KEY(entity_id,title,evidence_id));
                CREATE TABLE observations (
                    id TEXT PRIMARY KEY, entity_id TEXT NOT NULL REFERENCES entities(id),
                    kind TEXT NOT NULL CHECK(kind IN ('history_seen','liked','saved','watch_later')),
                    observed_at TEXT, collection_id TEXT, evidence_id TEXT NOT NULL REFERENCES evidence(id),
                    details TEXT NOT NULL);
                CREATE TABLE observation_sources (
                    observation_id TEXT REFERENCES observations(id), evidence_id TEXT REFERENCES evidence(id),
                    PRIMARY KEY(observation_id,evidence_id));
                CREATE TABLE concepts (
                    id TEXT PRIMARY KEY, label TEXT NOT NULL, kind TEXT NOT NULL,
                    evidence_id TEXT NOT NULL REFERENCES evidence(id));
                CREATE TABLE relationships (
                    id TEXT PRIMARY KEY, subject_id TEXT NOT NULL, predicate TEXT NOT NULL,
                    object_id TEXT NOT NULL, status TEXT NOT NULL
                    CHECK(status IN ('known','inferred','hypothesis')), confidence REAL NOT NULL
                    CHECK(confidence BETWEEN 0 AND 1), evidence_id TEXT NOT NULL REFERENCES evidence(id),
                    falsification TEXT NOT NULL);
                CREATE TABLE candidates (
                    id TEXT PRIMARY KEY, entity_id TEXT NOT NULL REFERENCES entities(id),
                    retrieval_path TEXT NOT NULL CHECK(retrieval_path IN ('catalog_gap','open_world')),
                    dedupe_key TEXT NOT NULL UNIQUE, facets TEXT NOT NULL, reasons TEXT NOT NULL,
                    uncertainty TEXT NOT NULL, evidence_id TEXT NOT NULL REFERENCES evidence(id));
                CREATE TABLE reviews (
                    entity_id TEXT PRIMARY KEY REFERENCES entities(id), decision TEXT NOT NULL,
                    reason TEXT NOT NULL, updated_at TEXT NOT NULL,
                    evidence_id TEXT NOT NULL REFERENCES evidence(id));
                CREATE TABLE checkpoints (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE playlist_annotations (
                    playlist_id TEXT PRIMARY KEY REFERENCES entities(id), purpose TEXT NOT NULL,
                    relevance TEXT NOT NULL, notes TEXT NOT NULL, reviewed INTEGER NOT NULL,
                    updated_at TEXT NOT NULL, evidence_id TEXT NOT NULL REFERENCES evidence(id));
                PRAGMA user_version=1;
                COMMIT;''')

    def close(self):
        self.db.close()

    def evidence(self, source_type, source_ref, *, completeness='unknown', notes=None,
                 visibility='private', confidence=1.0, observed_at=None, retrieved_at=None):
        if completeness not in COMPLETENESS:
            raise ValueError('Unknown completeness state')
        retrieved_at = retrieved_at or now()
        eid = stable_id(source_type, source_ref, retrieved_at, METHOD)
        self.db.execute('INSERT INTO evidence VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING',
                        (eid, source_type, source_ref, retrieved_at, observed_at, confidence,
                         visibility, METHOD, completeness, json.dumps(notes or {})))
        return eid

    def entity(self, eid, kind, native_id, title, evidence_id, *, url='', creator_id=None,
               published_at=None, availability='unknown', visibility='private'):
        # A private observation never upgrades an object to public export eligibility.
        self.db.execute('''INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
            title=CASE WHEN excluded.title='' THEN entities.title ELSE excluded.title END,
            creator_id=coalesce(excluded.creator_id,entities.creator_id),
            published_at=coalesce(excluded.published_at,entities.published_at),
            availability=excluded.availability,
            visibility=CASE WHEN entities.visibility='private' THEN 'private' ELSE excluded.visibility END,
            evidence_id=excluded.evidence_id''',
                        (eid, kind, native_id, url, title, creator_id, published_at,
                         availability, visibility, evidence_id))
        if title:
            self.db.execute('INSERT OR IGNORE INTO titles VALUES (?,?,?)', (eid, title, evidence_id))
        return eid

    def observe(self, oid, entity_id, kind, observed_at, evidence_id, *, collection=None, details=None):
        self.db.execute('INSERT OR IGNORE INTO observations VALUES (?,?,?,?,?,?,?)',
                        (oid, entity_id, kind, observed_at, collection, evidence_id,
                         json.dumps(details or {})))
        inserted = self.db.execute('SELECT changes()').fetchone()[0]
        self.db.execute('INSERT OR IGNORE INTO observation_sources VALUES (?,?)', (oid, evidence_id))
        return inserted

    def checkpoint(self, key, value):
        self.db.execute('INSERT INTO checkpoints VALUES (?,?) ON CONFLICT(key) '
                        'DO UPDATE SET value=excluded.value', (key, json.dumps(value)))

    def get_checkpoint(self, key, default=None):
        row = self.db.execute('SELECT value FROM checkpoints WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def review(self, entity_id, decision, reason):
        if decision not in ('keep', 'skip', 'later', 'already_watched', 'unknown'):
            raise ValueError('Unsupported review decision')
        with self.db:
            eid = self.evidence('manual_review', entity_id, notes={'decision': decision, 'reason': reason})
            self.db.execute('INSERT INTO reviews VALUES (?,?,?,?,?) ON CONFLICT(entity_id) '
                            'DO UPDATE SET decision=excluded.decision,reason=excluded.reason,'
                            'updated_at=excluded.updated_at,evidence_id=excluded.evidence_id',
                            (entity_id, decision, reason, now(), eid))

    def coverage(self):
        counts = {name: self.db.execute('SELECT count(*) FROM ' + name).fetchone()[0]
                  for name in ('entities', 'observations', 'evidence', 'reviews')}
        sources = [dict(row) for row in self.db.execute(
            'SELECT source_type,completeness,count(*) AS snapshots FROM evidence '
            'GROUP BY source_type,completeness')]
        return {'schema_version': SCHEMA_VERSION, 'counts': counts, 'sources': sources,
                'watch_minutes': 'not_measurable', 'fractional_completion': 'not_measurable',
                'time_to_50_percent': 'not_measurable',
                'history_coverage': 'Available records only; absence is not proof of never watched.'}
