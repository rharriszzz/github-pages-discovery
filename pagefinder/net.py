"""Persistent cache and conservative request admission shared by network clients.

Reservation is atomic across processes. A failed request consumes its reservation.
No credential, authorization header, or OAuth endpoint belongs in this cache.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
from pathlib import Path
import sqlite3
import time
from zoneinfo import ZoneInfo


class BudgetExceeded(Exception):
    pass


class ResponseError(Exception):
    pass


def quota_day(now):
    return datetime.fromtimestamp(now, ZoneInfo('America/Los_Angeles')).date().isoformat()


def next_quota_day(now):
    local = datetime.fromtimestamp(now, ZoneInfo('America/Los_Angeles'))
    return datetime.combine(local.date() + timedelta(days=1), datetime.min.time(),
                            local.tzinfo).timestamp()


class NetworkState:
    def __init__(self, path: Path, clock=time.time):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=10)
        self.db.execute('PRAGMA busy_timeout=10000')
        self.clock = clock
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS http_attempts (
                service TEXT NOT NULL, at REAL NOT NULL, units INTEGER NOT NULL, day TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS http_attempt_window ON http_attempts(service, at);
            CREATE TABLE IF NOT EXISTS http_cooldowns (service TEXT PRIMARY KEY, until REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS http_results (
                key TEXT NOT NULL, fetched REAL NOT NULL, status INTEGER NOT NULL,
                headers TEXT NOT NULL, body TEXT NOT NULL, digest TEXT NOT NULL,
                PRIMARY KEY(key, fetched, digest));
            CREATE INDEX IF NOT EXISTS http_result_lookup ON http_results(key, fetched);
        ''')

    def close(self):
        self.db.close()

    @staticmethod
    def key(url):
        return hashlib.sha256(url.encode()).hexdigest()

    def cached(self, url):
        row = self.db.execute('SELECT fetched,status,headers,body FROM http_results '
                              'WHERE key=? ORDER BY fetched DESC, rowid DESC LIMIT 1',
                              (self.key(url),)).fetchone()
        if row:
            return {'fetched': row[0], 'status': row[1], 'headers': json.loads(row[2]),
                    'body': json.loads(row[3])}

    def save(self, url, status, headers, body):
        # Keep all versions, including unsuccessful API responses, for local inspection.
        headers = {str(k).lower(): str(v) for k, v in headers.items() if str(k).lower() in
                   {'etag', 'retry-after', 'x-ratelimit-remaining', 'x-ratelimit-reset',
                    'x-ratelimit-limit', 'x-ratelimit-resource', 'content-type'}}
        encoded = json.dumps(body, sort_keys=True)
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO http_results VALUES (?,?,?,?,?,?)',
                            (self.key(url), self.clock(), status, json.dumps(headers), encoded,
                             hashlib.sha256(encoded.encode()).hexdigest()))

    def reserve(self, service, *, interval=1.0, window=3600, limit=60,
                daily_units=None, units=1):
        now = self.clock()
        self.db.execute('BEGIN IMMEDIATE')
        try:
            row = self.db.execute('SELECT until FROM http_cooldowns WHERE service=?',
                                  (service,)).fetchone()
            until = row[0] if row else 0
            count, last = self.db.execute(
                'SELECT count(*),max(at) FROM http_attempts WHERE service=? AND at>?',
                (service, now - window)).fetchone()
            if count >= limit:
                oldest = self.db.execute('SELECT min(at) FROM http_attempts WHERE service=? AND at>?',
                                         (service, now - window)).fetchone()[0]
                until = max(until, oldest + window)
            if daily_units is not None:
                used = self.db.execute('SELECT coalesce(sum(units),0) FROM http_attempts '
                                       'WHERE service=? AND day=?', (service, quota_day(now))).fetchone()[0]
                if used + units > daily_units:
                    until = max(until, next_quota_day(now))
            if until > now:
                raise BudgetExceeded('Request budget/cooldown reached; retry after ' +
                                     datetime.fromtimestamp(until, timezone.utc).isoformat())
            wait = max(0, (last or 0) + interval - now)
            if wait > 0:
                # Caller can sleep briefly and retry admission; no reservation yet.
                self.db.rollback()
                return wait
            self.db.execute('INSERT INTO http_attempts VALUES (?,?,?,?)',
                            (service, now, units, quota_day(now)))
            self.db.commit()
            return 0
        except BaseException:
            self.db.rollback()
            raise

    def admit(self, service, *, sleep=time.sleep, **policy):
        while True:
            wait = self.reserve(service, **policy)
            if not wait:
                return
            if wait > 30:
                raise BudgetExceeded('Request pacing requires a later rerun')
            sleep(wait)

    def response_limits(self, service, status, headers, *, quota_exhausted=False):
        now = self.clock()
        h = {k.lower(): str(v) for k, v in headers.items()}
        until = 0
        if status in (403, 429):
            until = now + 60  # Stop this batch even without usable rate headers.
        if h.get('retry-after'):
            try:
                until = max(until, now + float(h['retry-after']))
            except ValueError:
                try:
                    until = max(until, parsedate_to_datetime(h['retry-after']).timestamp())
                except (ValueError, TypeError):
                    pass
        if h.get('x-ratelimit-remaining') == '0':
            try:
                until = max(until, float(h['x-ratelimit-reset']) + 1)
            except (KeyError, ValueError):
                until = max(until, now + 3600)
        if quota_exhausted:
            until = max(until, next_quota_day(now))
        if until:
            with self.db:
                self.db.execute('INSERT INTO http_cooldowns VALUES (?,?) ON CONFLICT(service) '
                                'DO UPDATE SET until=max(until,excluded.until)', (service, until))

    def usage(self):
        return [dict(service=r[0], attempts=r[1], reserved_units=r[2]) for r in
                self.db.execute('SELECT service,count(*),sum(units) FROM http_attempts GROUP BY service')]
