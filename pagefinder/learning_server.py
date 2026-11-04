"""Learning Queue on loopback, sharing creator routes and private HTTP defenses."""
from pathlib import Path
import secrets
import sqlite3
from urllib.parse import parse_qs, urlsplit

from .creators import apply_creator_feedback, creator_report, render_review, research_report
from .learning import refresh, search, feedback
from .private_server import PrivateHandler, loopback_server, run_server
from .research import Store


def page(token):
    root = Path(__file__).parent
    html = (root / 'learning_review.html').read_text()
    return html.replace('/*STYLE*/', (root / 'learning_review.css').read_text()).replace(
        '/*SCRIPT*/', 'const TOKEN=' + __import__('json').dumps(token) + ';\n' + (root / 'learning_review.js').read_text())


def make_learning_server(folder, port=8767, arxiv_dir=None):
    if not 0 <= port <= 65535:
        raise ValueError('Port must be between 0 and 65535')
    folder = Path(folder)
    store = Store(folder)
    try:
        refresh(store, arxiv_dir)
    finally:
        store.close()
    token = secrets.token_urlsafe(32)
    homepage = page(token).encode()

    class Handler(PrivateHandler):
        def do_GET(self):
            if not self.valid_host():
                return self.json(403, {})
            parsed = urlsplit(self.path)
            if parsed.path not in ('/', '/api/search', '/api/status', '/creators', '/report', '/learning-report'):
                return self.json(404, {})
            if parsed.path == '/':
                return self.reply(200, homepage, 'text/html')
            store = None
            try:
                store = Store(folder)
                if parsed.path == '/api/search':
                    args = parse_qs(parsed.query, keep_blank_values=True)
                    if set(args) - {'q', 'goal', 'time', 'format', 'view'} or any(len(v) != 1 for v in args.values()):
                        raise ValueError('Invalid search parameters')
                    return self.json(200, search(store, args.pop('q', [''])[0], **{k: v[0] for k, v in args.items()}))
                if parsed.path == '/api/status':
                    return self.json(200, store.get_checkpoint('learning_sources', {}))
                if parsed.path == '/learning-report':
                    report = folder / 'learning_research_report.md'
                    return self.reply(200, report.read_bytes() if report.exists() else b'No additional research report is installed yet.', 'text/plain')
                report = creator_report(store)
                if parsed.path == '/report':
                    return self.reply(200, research_report(report).encode(), 'text/plain')
                html = render_review(report, token=token).replace('href="/" id="refresh"', 'href="/creators" id="refresh"')
                return self.reply(200, html.replace('<body>', '<body><nav><a href="/">Back to Learning Queue</a></nav>').encode(), 'text/html')
            except (ValueError, TypeError, KeyError):
                return self.json(400, {'error': 'The search options or requested collection could not be read.'})
            except (OSError, sqlite3.Error):
                return self.json(503, {'error': 'Private storage is unavailable. Check permissions, space and database access.'})
            finally:
                if store:
                    store.close()

        def do_POST(self):
            if not self.valid_write(token):
                return self.json(403, {})
            if self.path not in ('/api/learning-feedback', '/api/refresh', '/api/review'):
                return self.json(404, {})
            store = None
            try:
                data = self.payload(maximum=100_000 if self.path != '/api/review' else 20_000_000)
                store = Store(folder)
                if self.path == '/api/refresh':
                    return self.json(200, refresh(store))
                if self.path == '/api/review':
                    apply_creator_feedback(store, data)
                    return self.json(200, {'saved': True})
                return self.json(200, feedback(store, data))
            except (ValueError, TypeError, KeyError):
                return self.json(400, {'error': 'Invalid feedback. Check the work, action and note length.'})
            except (OSError, sqlite3.Error):
                return self.json(503, {'error': 'Private changes could not be saved. Your text is still in the browser; check storage access and space.'})
            finally:
                if store:
                    store.close()

    return loopback_server(Handler, port)


def serve_learning(folder, port=8767, arxiv_dir=None):
    run_server(make_learning_server(folder, port, arxiv_dir), 'Private Learning Queue')
