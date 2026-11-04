"""Private research CLI. Never used by the public Pages build."""
from __future__ import annotations

import argparse
import errno
import json
import sqlite3
import sys

from .net import BudgetExceeded, ResponseError
from .bookmarks import import_bookmarks
from .interests import import_bookshelf, import_interest_notes, set_interest_scope, write_interest_graph, DEFAULT_SOURCE
from .candidates import import_candidate_batch, write_review_queue
from .creator_sources import import_collection, channel_seeds, inspect_metadata
from .creators import import_creator_batch, write_creator_review, apply_creator_feedback, DECISIONS
from .privacy import config_dir, data_dir, private_json
from .research import Store
from .takeout import import_takeout
from .youtube import GoogleTransport, YouTubeClient, annotate, authenticate, inventory


def _safe_error_message(exc):
    # File/parser/database errors may contain private paths, titles or credentials.
    # Only application-authored messages and fixed OS error names are safe to print.
    if isinstance(exc, (BudgetExceeded, ResponseError)) or type(exc) is ValueError:
        return str(exc)
    if isinstance(exc, OSError):
        messages = {
            errno.EROFS: 'Private storage is read-only. Run from a terminal with write access '
                         'to the private data directory, or allow that access in the sandbox.',
            errno.EACCES: 'Permission denied. Check access to private files and permission '
                          'to bind a loopback socket when starting a local server.',
            errno.EPERM: 'Operation not permitted. Check sandbox restrictions and permissions '
                         'for private storage and local sockets.',
            errno.EADDRINUSE: 'Local port is already in use. Choose another --port '
                              '(for example, --port 8767 for serve-creators or --port 8768 '
                              'for serve-learning), or stop the existing server.',
            errno.ENOENT: 'Required file or directory was not found. Check input paths '
                          'and setup instructions.',
            errno.ENOSPC: 'No space left on the device. Free space on the private storage device.',
        }
        message = messages.get(exc.errno, 'Filesystem or local socket operation failed. '
                               'Check private paths, permissions and setup instructions.')
        code = errno.errorcode.get(exc.errno)
        return f'{message} ({code})' if code else message
    if isinstance(exc, sqlite3.Error):
        return ('Private SQLite operation failed. Check database permissions, available space '
                'and whether another process is holding a database lock.')
    return 'Check input format, private paths, permissions and setup instructions.'


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
    shelf = sub.add_parser('import-bookshelf', help='Import title-level bookshelf evidence and curated concept hypotheses')
    shelf.add_argument('source', nargs='?', default=str(DEFAULT_SOURCE))
    shelf.add_argument('--overall-reading-completion', choices=('unknown', 'low', 'partial', 'high'),
                       help='Optional private user-reported aggregate; never assigns per-book completion')
    sub.add_parser('interest-graph', help='Regenerate the private bookshelf graph with durable manual feedback')
    notes = sub.add_parser('import-interest-notes', help='Import private explicit interests/background, with hypotheses kept separate')
    notes.add_argument('source')
    batch = sub.add_parser('import-candidate-batch', help='Create a private review queue from a bounded cached research batch')
    batch.add_argument('source')
    sub.add_parser('review-queue', help='Regenerate the private candidate queue with saved feedback')
    collection = sub.add_parser('creator-sources', help='Bounded reviewed-positive playlist or recent Likes import')
    source_group = collection.add_mutually_exclusive_group(required=True)
    source_group.add_argument('--playlist-id')
    source_group.add_argument('--likes', action='store_true')
    collection.add_argument('--max-pages', type=int, default=2)
    collection.add_argument('--max-requests', type=int, default=12)
    collection.add_argument('--daily-units', type=int, default=100)
    collection.add_argument('--offline', action='store_true')
    sub.add_parser('creator-seeds', help='Build a private channel sampling frame from imported observations')
    metadata = sub.add_parser('creator-metadata', help='Cached public metadata for a bounded private ID selection')
    metadata.add_argument('source')
    metadata.add_argument('--offline', action='store_true')
    metadata.add_argument('--max-requests', type=int, default=12)
    metadata.add_argument('--daily-units', type=int, default=100)
    creators = sub.add_parser('import-creators', help='Import an assessed private cross-platform experiment')
    creators.add_argument('source')
    sub.add_parser('creator-review', help='Regenerate the private creator dashboard and research report')
    feedback = sub.add_parser('creator-feedback', help='Import downloaded creator review decisions')
    feedback.add_argument('source')
    server = sub.add_parser('serve-creators', help='Serve private durable reviews on 127.0.0.1 only')
    server.add_argument('--port', type=int, default=8766)
    learning = sub.add_parser('serve-learning', help='Serve the private work-level Learning Queue; refresh local sources without network')
    learning.add_argument('--port', type=int, default=8767)
    learning.add_argument('--arxiv-dir', help='Read-only arXiv Shelf working tree; remembered privately')
    learning_refresh = sub.add_parser('refresh-learning', help='Refresh the work index from local sources only')
    learning_refresh.add_argument('--arxiv-dir')
    learning_research = sub.add_parser('import-learning-research', help='Import a private, source-linked assessed-work manifest')
    learning_research.add_argument('source')
    scope = sub.add_parser('set-interest-scope', help='Persist an explicit private application constraint on a baseline topic')
    scope.add_argument('topic')
    scope.add_argument('--label', required=True)
    scope.add_argument('--context', action='append', required=True, help='Repeat for each required-context keyword alternative')
    scope.add_argument('--project-status', choices=('unspecified', 'active', 'stopped'), default='unspecified')
    scope.add_argument('--mode', choices=('require', 'prefer'), default='require',
                       help='Require context, or prefer it while allowing a small exploratory supplement')
    scope.add_argument('--note', default='')
    rev = sub.add_parser('review', help='Persist explicit manual feedback independently of recomputation')
    rev.add_argument('entity_id')
    rev.add_argument('decision', choices=tuple(dict.fromkeys(('keep', 'skip', 'later', 'already_watched', *DECISIONS))))
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
        elif args.command == 'import-bookshelf':
            report = import_bookshelf(store, args.source, overall_reading_completion=args.overall_reading_completion)
            print('Bookshelf:', len(report['books']), 'volumes;', len(report['hypotheses']), 'exploratory questions')
            print('Private graph report:', folder / 'interest_graph.html')
            print('No reading events or preference weights assigned; public keyword baseline unchanged.')
        elif args.command == 'interest-graph':
            write_interest_graph(store)
            print('Private graph regenerated:', folder / 'interest_graph.html')
        elif args.command == 'import-interest-notes':
            context = import_interest_notes(store, args.source)
            print('Private interest notes saved:', sum(len(records) for records in context.values()), 'records')
        elif args.command == 'import-candidate-batch':
            report = import_candidate_batch(store, args.source)
            print('Private candidates ready for review:', len(report['candidates']))
            print('Local viewer:', folder / 'discovery_queue.html')
        elif args.command == 'review-queue':
            write_review_queue(store)
            print('Private review queue regenerated:', folder / 'discovery_queue.html')
        elif args.command == 'creator-sources':
            client = YouTubeClient(store, GoogleTransport(config), offline=args.offline,
                                   max_requests=args.max_requests, daily_units=args.daily_units)
            state = import_collection(store, client, playlist_id=args.playlist_id, likes=args.likes,
                                      max_pages=args.max_pages)
            print('Collection pages:', state['pages'], 'items:', state['items'], 'complete:', state['complete'])
            print('API attempts:', client.requests, 'cache hits:', client.cache_hits)
            print('Private channel frame:', len(channel_seeds(store)['channels']))
        elif args.command == 'creator-seeds':
            print('Private channel frame:', len(channel_seeds(store)['channels']))
        elif args.command == 'creator-metadata':
            client = YouTubeClient(store, GoogleTransport(config), offline=args.offline,
                                   max_requests=args.max_requests, daily_units=args.daily_units)
            report = inspect_metadata(store, client, args.source)
            print('Cached channels:', len(report['channels']), 'videos:', len(report['videos']))
            print('API attempts:', client.requests, 'cache hits:', client.cache_hits)
        elif args.command == 'import-creators':
            report = import_creator_batch(store, args.source)
            print('Creator investigations:', report['metrics']['investigations'])
            print('Review candidates:', report['metrics']['recommendations'])
            print('Private viewer:', folder / 'creator_review.html')
        elif args.command == 'creator-review':
            write_creator_review(store)
            print('Private viewer:', folder / 'creator_review.html')
        elif args.command == 'creator-feedback':
            from .creators import _read
            apply_creator_feedback(store, json.loads(_read(args.source)))
            print('Creator feedback saved in the shared private review store.')
        elif args.command == 'serve-creators':
            from .creator_server import serve_creators
            store.close()
            store = None
            serve_creators(folder, args.port)
        elif args.command == 'serve-learning':
            from .learning_server import serve_learning
            store.close()
            store = None
            serve_learning(folder, args.port, args.arxiv_dir)
        elif args.command in ('refresh-learning', 'import-learning-research'):
            from .learning import refresh, import_research
            report = (import_research(store, args.source) if args.command == 'import-learning-research'
                      else refresh(store, args.arxiv_dir))
            print('Private Learning Queue:', report['index']['active_works'], 'works; no external requests.')
        elif args.command == 'set-interest-scope':
            set_interest_scope(store, args.topic, args.label, args.context,
                               project_status=args.project_status, note=args.note, mode=args.mode)
            print('Explicit scope correction saved privately; inferred topic breadth is overridden.')
        elif args.command == 'review':
            store.review(args.entity_id, args.decision, args.reason)
            if store.get_checkpoint('active_bookshelf_model'):
                write_interest_graph(store)
            if store.get_checkpoint('active_candidate_batch'):
                write_review_queue(store)
            if store.get_checkpoint('active_creator_batch'):
                write_creator_review(store)
            print('Manual feedback saved locally.')
        else:
            private_json(folder / 'evidence_coverage.json', store.coverage())
            print(json.dumps(store.coverage(), indent=2))
    except (ValueError, OSError, sqlite3.Error, BudgetExceeded, ResponseError) as exc:
        print('Stopped safely: ' + _safe_error_message(exc), file=sys.stderr)
        return 2
    finally:
        if client:
            client.close()
        if store:
            store.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
