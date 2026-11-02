import argparse
from pathlib import Path
import sys
from .core import ROOT, DB, ApiError, RateLimited, discover, enrich, load_json, save_json
from .report import render


def main():
    p = argparse.ArgumentParser(description='Discover, classify, rank and catalog GitHub Pages websites')
    sub = p.add_subparsers(dest='command', required=True)
    d = sub.add_parser('discover', help='Search public GitHub repositories; records are candidate URLs, not verified sites')
    d.add_argument('--queries-file', default='data/search_queries.txt')
    d.add_argument('--pages', type=int, default=1, help='Pages of up to 100 repositories per query')
    d.add_argument('--per-page', type=int, default=100)
    d.add_argument('--offline', action='store_true')
    d.add_argument('--delay', type=float, default=2.1)
    e = sub.add_parser('enrich', help='Validate live sites; check account types; read short HTML extracts')
    e.add_argument('--max-sites', type=int, default=30)
    e.add_argument('--offline', action='store_true')
    e.add_argument('--no-owner-api', action='store_true')
    e.add_argument('--delay', type=float, default=2.1)
    sub.add_parser('report', help='Generate HTML, JSON and CSV ranking, entirely offline')
    sub.add_parser('stats', help='Show current worklist counts')
    a = p.parse_args()
    try:
        if a.command == 'discover':
            path = ROOT / a.queries_file
            queries = [s.strip() for s in path.read_text(encoding='utf-8').splitlines()
                       if s.strip() and not s.lstrip().startswith('#')]
            for item in discover(queries, a.per_page, a.pages, a.offline, a.delay):
                print(item)
        elif a.command == 'enrich':
            print('Processed:', enrich(a.max_sites, a.offline, not a.no_owner_api, a.delay))
        elif a.command == 'report':
            render()
        else:
            rows = load_json(DB, [])
            from collections import Counter
            print(f'Records: {len(rows)}; account types: {dict(Counter(r.get("account_type", "Unknown") for r in rows))}')
            print(f'HTTP status: {dict(Counter(r.get("site_status", "unchecked") for r in rows))}')
    except (ApiError, OSError, ValueError) as exc:
        print(f'Stopped safely: {exc}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
