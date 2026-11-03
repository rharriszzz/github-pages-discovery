"""Loopback-only private review surface; no directory listing or external assets."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
import hmac
import json
import secrets
import sqlite3

from .creators import apply_creator_feedback, creator_report, render_review, research_report
from .research import Store


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

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # No personal URLs or decisions in server logs.

        def valid_host(self):
            return self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'

        def reply(self, status, body, kind='application/json'):
            try:
                self.send_response(status)
                self.send_header('Content-Type', kind + '; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self.send_header('Cache-Control', 'no-store')
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.send_header('X-Frame-Options', 'DENY')
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                # An individual request can close while the browser remains open.
                self.close_connection = True

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
            origin = f'http://127.0.0.1:{self.server.server_port}'
            if (not self.valid_host() or self.headers.get('Origin') != origin or
                    not hmac.compare_digest(self.headers.get('X-Review-Token', ''), token)):
                return self.reply(403, b'{}')
            if self.path != '/api/review':
                return self.reply(404, b'{}')
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 20_000_000 or self.headers.get('Content-Type') != 'application/json':
                    raise ValueError()
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise ValueError()
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

    return HTTPServer(('127.0.0.1', port), Handler)


def serve_creators(folder, port=8766):
    server = make_server(folder, port)
    print(f'Private creator review: http://127.0.0.1:{server.server_port}/', flush=True)
    print('Keep this terminal running. On WSL2, open the URL in your Windows browser. '
          'If Windows cannot connect, check WSL localhost forwarding; the service binds only to loopback.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
