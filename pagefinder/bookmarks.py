"""Import explicitly selected Chrome bookmark folders without visiting any URL.

Only the selected tree and whitelisted bookmark fields are persisted. The source
is opened read-only; no browser history or cookie files are opened.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import html
import json
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from .privacy import outside_repo, private_json, private_write
from .research import stable_id
from .takeout import video_id

PARSER_VERSION = 1
MAX_BYTES = 100_000_000
FIELDS = ('type', 'name', 'id', 'guid', 'url', 'date_added', 'date_modified')
LIMITATIONS = [
    'Only explicitly selected folders in this local profile snapshot are covered.',
    'Bookmarks indicate saving, not visits, enrollment, completion or current endorsement.',
    'Bookmark dates are not publication dates or viewing timestamps.',
    'Page content and current availability have not been checked.',
    'Older snapshots and memberships remain as historical evidence after moves/deletions.',
]


def chrome_time(value):
    """Chrome stores integer microseconds since 1601-01-01 UTC; zero is unknown."""
    if not isinstance(value, str) or not value.isascii() or not value.isdigit() or len(value) > 20:
        return None
    try:
        micros = int(value)
        if micros <= 0:
            return None
        return (datetime(1601, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=micros)).isoformat()
    except (OverflowError, ValueError):
        return None


def canonical_url(value):
    """Conservative identity: normalize host/default port, preserve query/fragment."""
    if not isinstance(value, str) or not value or any(c.isspace() or ord(c) < 32 for c in value):
        return None
    try:
        p = urlsplit(value)
        if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password:
            return None
        host = p.hostname.lower()
        if ':' in host:
            host = '[' + host + ']'
        if p.port and p.port != (443 if p.scheme == 'https' else 80):
            host += ':' + str(p.port)
        return urlunsplit((p.scheme, host, p.path or '/', p.query, p.fragment))
    except ValueError:
        return None


def _children(node):
    children = node.get('children', [])
    if not isinstance(children, list) or any(not isinstance(c, dict) for c in children):
        raise ValueError('Malformed Chrome folder children; no import performed')
    return children


def _filtered(node, depth=0):
    if depth > 100:
        raise ValueError('Bookmark nesting exceeds the supported depth')
    result = {key: node[key] for key in FIELDS if key in node}
    if node.get('type') == 'folder':
        result['children'] = [_filtered(child, depth + 1) for child in _children(node)]
    return result


def select_folders(document, selectors):
    if (not isinstance(document, dict) or type(document.get('version')) is not int or
            document['version'] != 1 or not isinstance(document.get('roots'), dict)):
        raise ValueError('Expected a Chrome Bookmarks version 1 JSON file')
    if not selectors or any(not isinstance(s, str) or not s.strip() for s in selectors):
        raise ValueError('Explicit bookmark folder selection is required')
    selectors = [s.strip().casefold() for s in selectors]
    if len(set(selectors)) != len(selectors):
        raise ValueError('Duplicate bookmark folder selector')
    matches = {s: [] for s in selectors}
    stack = [((key,), node) for key, node in document['roots'].items() if isinstance(node, dict)]
    visited = 0
    while stack:
        path, node = stack.pop()
        visited += 1
        if visited > 1_000_000 or len(path) > 100:
            raise ValueError('Bookmark tree exceeds the supported size/depth')
        if node.get('type') != 'folder':
            continue
        name = node.get('name')
        if not isinstance(name, str):
            raise ValueError('Malformed Chrome folder name; no import performed')
        for selector in selectors:
            if (name.casefold() == selector if '/' not in selector else
                    '/'.join(path).casefold() == selector):
                matches[selector].append((path, node))
        for child in reversed(_children(node)):
            if child.get('type') == 'folder':
                child_name = child.get('name')
                if not isinstance(child_name, str):
                    raise ValueError('Malformed Chrome folder name; no import performed')
                stack.append(((*path, child_name), child))
    if any(len(value) != 1 for value in matches.values()):
        raise ValueError('Folder selection is missing or ambiguous; use a full root/folder path')
    selected = [value[0] for value in matches.values()]
    paths = [path for path, node in selected]
    if any(a != b and a == b[:len(a)] for a in paths for b in paths):
        raise ValueError('Select separate folders rather than overlapping parent/child trees')
    return [{'path': list(path), 'node': _filtered(node)} for path, node in selected]


def import_bookmarks(store, source, selectors):
    source = outside_repo(source)
    with source.open('rb') as handle:
        raw = handle.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('Chrome Bookmarks file exceeds the 100 MB safety bound')
    try:
        document = json.loads(raw)
    except (ValueError, RecursionError):
        raise ValueError('Cannot parse Chrome Bookmarks JSON; retry after Chrome finishes saving') from None
    selected = select_folders(document, selectors)
    snapshot = {'version': 1, 'parser_version': PARSER_VERSION, 'visibility': 'private',
                'source_type': 'chrome_bookmarks_subset', 'source_ref': str(source), 'folders': selected}
    encoded = (json.dumps(snapshot, sort_keys=True, ensure_ascii=False) + '\n').encode()
    digest = hashlib.sha256(encoded).hexdigest()
    snapshot_path = store.folder / 'sources' / ('chrome-bookmarks-' + digest + '.json')
    private_write(snapshot_path, encoded)
    report = {'version': 1, 'parser_version': PARSER_VERSION, 'visibility': 'private',
              'source_snapshot': str(snapshot_path), 'source_sha256': digest,
              'completeness': 'complete_for_request', 'limitations': LIMITATIONS,
              'folders': [], 'bookmarks': [], 'bookmark_nodes': 0, 'excluded': 0,
              'missing_or_invalid_added_dates': 0, 'new_saved_memberships': 0,
              'existing_or_duplicate_memberships': 0, 'external_requests': 0}
    def node_id(node, path):
        native = node.get('guid') or node.get('id')
        if isinstance(node.get('guid'), str) and node['guid']:
            return stable_id('chrome-guid', node['guid'])
        return stable_id('chrome-local', str(source), native, path, node.get('url'))
    unique_items, memberships = set(), set()
    with store.db:
        evidence = store.evidence('chrome_bookmarks', str(snapshot_path), completeness='complete_for_request',
                                  notes={'sha256': digest, 'parser_version': PARSER_VERSION,
                                         'limitations': LIMITATIONS})
        for selection in selected:
            before = report['bookmark_nodes']
            stack = [(selection['path'], selection['node'], None)]
            while stack:
                path, node, collection = stack.pop()
                if node.get('type') == 'folder':
                    folder_id = 'chrome:folder:' + node_id(node, path)
                    store.entity(folder_id, 'bookmark_folder', folder_id, node.get('name', ''), evidence)
                    report['folders'].append({'id': folder_id, 'path': path,
                                              'date_added': chrome_time(node.get('date_added')),
                                              'date_modified': chrome_time(node.get('date_modified'))})
                    for child in reversed(_children(node)):
                        child_path = [*path, child.get('name', '')] if child.get('type') == 'folder' else path
                        stack.append((child_path, child, folder_id))
                    continue
                if node.get('type') != 'url':
                    report['excluded'] += 1
                    continue
                report['bookmark_nodes'] += 1
                url, title = canonical_url(node.get('url')), node.get('name', '')
                if url is None or not isinstance(title, str):
                    report['excluded'] += 1
                    continue
                vid = video_id(url)
                entity_id = 'youtube:video:' + vid if vid else 'web:page:' + stable_id(url)
                store.entity(entity_id, 'youtube_video' if vid else 'web_page', vid or url, title, evidence,
                             url='https://www.youtube.com/watch?v=' + vid if vid else url)
                added = chrome_time(node.get('date_added'))
                if added is None:
                    report['missing_or_invalid_added_dates'] += 1
                details = {'source': 'chrome_bookmark', 'bookmark_id': node_id(node, path),
                           'folder_path': path, 'bookmark_title': title, 'bookmark_url': url,
                           'date_added_raw': node.get('date_added'),
                           'date_modified_raw': node.get('date_modified'),
                           'signal_interpretation': 'saved_interest_only'}
                inserted = store.observe(stable_id('chrome_saved', entity_id, collection), entity_id,
                                         'saved', added, evidence, collection=collection, details=details)
                report['new_saved_memberships'] += inserted
                report['existing_or_duplicate_memberships'] += 1 - inserted
                unique_items.add(entity_id)
                memberships.add((entity_id, collection))
                report['bookmarks'].append({'entity_id': entity_id, 'folder_id': collection,
                                            'folder_path': path, 'title': title, 'url': url,
                                            'date_added': added,
                                            'date_modified': chrome_time(node.get('date_modified'))})
            selection['bookmark_nodes'] = report['bookmark_nodes'] - before
        report['selected_folders'] = [{'path': s['path'], 'bookmark_nodes': s['bookmark_nodes']} for s in selected]
        report['unique_items'] = len(unique_items)
        report['saved_memberships'] = len(memberships)
        store.checkpoint('chrome_bookmarks:' + stable_id(str(source), sorted(selectors)), report)
    private_json(store.folder / 'imports' / ('chrome-bookmarks-' + digest + '.json'), report)
    private_json(store.folder / 'bookmark_inventory.json', report)
    write_viewer(store.folder / 'bookmark_inventory.html', report)
    private_json(store.folder / 'evidence_coverage.json', store.coverage())
    return report


def write_viewer(path: Path, report):
    h = lambda value: html.escape(str(value or ''), quote=True)
    rows = ''.join('<tr><td>' + h(' / '.join(r['folder_path'])) + '</td><td><a href="' + h(r['url']) +
                   '" target="_blank" rel="noopener noreferrer">' + h(r['title'] or r['url']) +
                   '</a><br><small>' + h(r['url']) + '</small></td><td>' +
                   h(r['date_added'] or 'unknown') + '</td></tr>' for r in report['bookmarks'])
    page = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'none'; base-uri 'none'; form-action 'none'">
<title>Private bookmark inventory</title><style>
body{font:16px system-ui;background:#fafbfc;color:#172b40;margin:2rem}table{border-collapse:collapse;width:100%;background:white}
th,td{padding:.8rem;border-bottom:1px solid #dde3e9;text-align:left;vertical-align:top}input{font:inherit;padding:.5rem}small{overflow-wrap:anywhere}
</style><h1>Private bookmark inventory</h1><p>Saved interests only; visits, enrollment and completion are unknown.
Dates record bookmark creation, not publication. Pages have not been fetched.</p><p>''' + h(
        f"{report['bookmark_nodes']} bookmark entries; {report['unique_items']} unique items; {report['excluded']} excluded; zero external requests.") + '''</p>
<label>Filter <input id="filter" type="search"></label><p id="count"></p>
<table><thead><tr><th>Folder</th><th>Bookmark</th><th>Added (UTC)</th></tr></thead><tbody>''' + rows + '''</tbody></table>
<script>const rows=[...document.querySelectorAll('tbody tr')],count=document.querySelector('#count');
function filter(){const value=document.querySelector('#filter').value.toLowerCase();let shown=0;for(const r of rows){r.hidden=!r.textContent.toLowerCase().includes(value);if(!r.hidden)shown++}count.textContent=shown+' entries shown'}
document.querySelector('#filter').addEventListener('input',filter);filter();</script></html>'''
    private_write(path, page.encode())
