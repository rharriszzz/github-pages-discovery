"""Loopback-only private review surface; no directory listing or external assets."""
from __future__ import annotations

import secrets
import sqlite3

from .creators import apply_creator_feedback, creator_report, render_review, research_report
from .research import Store
from .private_server import PrivateHandler, loopback_server, run_server


def make_server(folder, port=8766):
    if not 0 <= port <= 65535:
        raise ValueError('Port must be between 0 and 65535')
    # Fail before advertising a URL if the collection cannot be loaded.
    store = Store(folder)
    try:
        creator_report(store)
    finally:
        store.close()
    token = secrets.token_urlsafe(32)

    class Handler(PrivateHandler):
        def do_GET(self):
            if not self.valid_host():
                return self.reply(403, b'{}')
            if self.path not in ('/', '/report'):
                return self.reply(404, b'{}')
            store = None
            try:
                store = Store(folder)
                report = creator_report(store)
                if self.path == '/report':
                    self.reply(200, research_report(report).encode(), 'text/plain')
                else:
                    page = render_review(report, token=token)
                    self.reply(200, page.encode(), 'text/html')
            except (OSError, sqlite3.Error, ValueError):
                self.reply(503, b'{"error":"Private collection could not be read. Check storage permissions, free space and database access; restart serve-creators for a startup diagnostic."}')
            finally:
                if store:
                    store.close()

        def do_POST(self):
            if not self.valid_write(token):
                return self.reply(403, b'{}')
            if self.path != '/api/review':
                return self.reply(404, b'{}')
            try:
                payload = self.payload()
                store = Store(folder)
                try:
                    apply_creator_feedback(store, payload)
                finally:
                    store.close()
            except (ValueError, KeyError, TypeError):
                return self.reply(400, b'{"error":"Invalid creator feedback"}')
            except (OSError, sqlite3.Error):
                return self.reply(503, b'{"error":"Private feedback could not be saved. Check storage permissions, free space and database access. Your browser text is retained."}')
            self.reply(200, b'{"saved":true}')

    return loopback_server(Handler, port)


def serve_creators(folder, port=8766):
    run_server(make_server(folder, port), 'Private creator review')
