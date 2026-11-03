"""Private research CLI. Never used by the public Pages build."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys

from .net import BudgetExceeded, ResponseError
from .bookmarks import import_bookmarks
from .privacy import config_dir, data_dir, private_json
from .research import Store
from .takeout import import_takeout
from .youtube import GoogleTransport, YouTubeClient, annotate, authenticate, inventory


def main(argv=None):
    p = argparse.ArgumentParser(description='Private local research; all personal data stays outside Git')
    p.add_argument('--data-dir', help='Dedicated private directory outside any Git working tree')
    p.add_argument('--config-dir', help='Desktop OAuth configuration outside Git')
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('init', help='Initialize/migrate private SQLite storage and report its location')
    auth = sub.add_parser('auth', help='Open Google Desktop OAuth approval in the local browser')
    auth.add_argument('--port', type=int, default=0, help='Loopback port; default chooses an available port')
    auth.add_argument('--browser', help='Python webbrowser name; otherwise uses BROWSER/system default')
    inv = sub.add_parser('inventory', help='Owned-playlist names/counts/privacy only; no video import')
    inv.add_argument('--offline', action='store_true', help='Read cache only; no credentials needed')
    inv.add_argument('--refresh', action='store_true', help='Start a fresh inventory; old responses retained')
    inv.add_argument('--max-pages', type=int, default=100)
    inv.add_argument('--max-requests', type=int, default=100, help='Attempt budget, including retries')
    inv.add_argument('--daily-units', type=int, default=9000, help='Persisted YouTube quota ceiling, Pacific day')
    ann = sub.add_parser('annotate', help='Apply downloaded/edited playlist annotation JSON')
    ann.add_argument('source')
    imp = sub.add_parser('import-takeout', help='Import one explicitly selected extracted source; cached locally')
    imp.add_argument('source')
    imp.add_argument('--kind', choices=('history', 'likes', 'watch_later', 'playlist'), required=True)
    imp.add_argument('--playlist-id', help='Required for a reviewed curated playlist')
    bookmarks = sub.add_parser('import-bookmarks', help='Import selected Chrome folders locally; no page requests')
    bookmarks.add_argument('source', help='Chrome profile Bookmarks JSON file outside Git')
    bookmarks.add_argument('--folder', action='append', required=True,
                           help='Repeat for each folder; use root/folder path when names are ambiguous')
    rev = sub.add_parser('review', help='Persist explicit manual feedback independently of recomputation')
    rev.add_argument('entity_id')
    rev.add_argument('decision', choices=('keep', 'skip', 'later', 'already_watched', 'unknown'))
    rev.add_argument('--reason', required=True)
    sub.add_parser('coverage', help='Write private coverage report; never infer unmeasured progress')
    args = p.parse_args(argv)
    store = client = None
    try:
        folder, config = data_dir(args.data_dir), config_dir(args.config_dir)
        if args.command == 'auth':
            print('Opening Google approval; callback binds to 127.0.0.1. No secrets will be printed.')
            authenticate(config, port=args.port, browser=args.browser)
            print('Read-only authorization saved outside Git.')
            return 0
        store = Store(folder)
        if args.command == 'init':
            print('Private SQLite schema initialized at:', folder)
        elif args.command == 'inventory':
            if args.refresh and args.offline:
                raise ValueError('--refresh requires network; omit it for cached/offline use')
            client = YouTubeClient(store, GoogleTransport(config), offline=args.offline,
                                   max_requests=args.max_requests, daily_units=args.daily_units)
            state = inventory(store, client, refresh=args.refresh, max_pages=args.max_pages)
            print('Inventory:', 'complete for request' if state['complete'] else 'partial; rerun to resume')
            print('Local editable report:', folder / 'playlist_inventory.html')
            print(f'API attempts this run: {client.requests}; cache hits: {client.cache_hits}')
            print('Review purposes/relevance before any playlist video import.')
        elif args.command == 'annotate':
            print('Annotations applied:', annotate(store, args.source))
        elif args.command == 'import-takeout':
            report = import_takeout(store, args.source, args.kind, playlist_id=args.playlist_id)
            print('Import complete:', report['imported_observations'], 'new observations;',
                  report['duplicates'], 'duplicates;', report['unavailable_or_unrecognized'], 'unrecognized rows')
            print('Private completeness report:', folder / 'imports')
        elif args.command == 'import-bookmarks':
            report = import_bookmarks(store, args.source, args.folder)
            print('Bookmarks:', report['bookmark_nodes'], 'entries;', report['unique_items'], 'unique items;',
                  report['new_saved_memberships'], 'new saved memberships;', report['excluded'], 'excluded')
            print('Private local viewer:', folder / 'bookmark_inventory.html')
            print('External requests: 0. Bookmarks indicate saving; visits and completion remain unknown.')
        elif args.command == 'review':
            store.review(args.entity_id, args.decision, args.reason)
            print('Manual feedback saved locally.')
        else:
            private_json(folder / 'evidence_coverage.json', store.coverage())
            print(json.dumps(store.coverage(), indent=2))
    except (ValueError, OSError, sqlite3.Error, BudgetExceeded, ResponseError):
        # File/parser errors can include private titles, paths and raw credential fields.
        # Known application messages are constructed without source content.
        exc = sys.exception() if hasattr(sys, 'exception') else sys.exc_info()[1]
        if isinstance(exc, (BudgetExceeded, ResponseError)) or type(exc) is ValueError:
            message = str(exc)
        else:
            message = 'Check input format, private paths, permissions and setup instructions.'
        print('Stopped safely: ' + message, file=sys.stderr)
        return 2
    finally:
        if client:
            client.close()
        if store:
            store.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
