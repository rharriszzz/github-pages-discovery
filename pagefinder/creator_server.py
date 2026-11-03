"""Loopback-only private review surface; no directory listing or external assets."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
import hmac
import json
import secrets

from .creators import apply_creator_feedback, creator_report, render_review, research_report
from .research import Store


def make_server(folder, port=8766):
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # No personal URLs or decisions in server logs.

        def valid_host(self):
            return self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'

        def reply(self, status, body, kind='application/json'):
            self.send_response(status)
            self.send_header('Content-Type', kind + '; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if not self.valid_host():
                return self.reply(403, b'{}')
            if self.path not in ('/', '/report'):
                return self.reply(404, b'{}')
            store = Store(folder)
            try:
                report = creator_report(store)
                if self.path == '/report':
                    self.reply(200, research_report(report).encode(), 'text/plain')
                else:
                    page = render_review(report, token=token)
                    self.reply(200, page.encode(), 'text/html')
            finally:
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
                if not 0 < length <= 100_000 or self.headers.get('Content-Type') != 'application/json':
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
            self.reply(200, b'{"saved":true}')

    return HTTPServer(('127.0.0.1', port), Handler)


def serve_creators(folder, port=8766):
    server = make_server(folder, port)
    print(f'Private creator review: http://127.0.0.1:{server.server_port}/', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
