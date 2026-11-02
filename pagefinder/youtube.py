"""Read-only, metadata-only YouTube playlist inventory and local review artifacts."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import html
import io
import json
from pathlib import Path
import re
import time
from urllib.parse import urlencode

from .net import BudgetExceeded, NetworkState, ResponseError
from .privacy import outside_repo, private_dir, private_json, private_write
from .research import now

SCOPE = 'https://www.googleapis.com/auth/youtube.readonly'
BASE = 'https://www.googleapis.com/youtube/v3/'
PURPOSES = ('unknown', 'favorites', 'reference', 'inbox', 'queue', 'archive', 'other')
RELEVANCE = ('unknown', 'positive', 'neutral', 'negative')
SYSTEM_COLLECTIONS = {
    'likes': 'Separate videos.list(myRating=like); most recent 1000 maximum; not fetched.',
    'watch_later': 'Items inaccessible through the Data API; use an explicitly selected Takeout export.',
    'history': 'Inaccessible through the Data API; use an explicitly selected Takeout export.',
}


def authenticate(folder: Path, *, port=0, browser=None):
    folder = private_dir(folder)
    secret = outside_repo(folder / 'client_secret.json')
    if not secret.is_file():
        raise ValueError('Desktop client_secret.json is missing; see docs/youtube_setup.md')
    config = json.loads(secret.read_text(encoding='utf-8'))
    if not isinstance(config, dict) or not isinstance(config.get('installed'), dict):
        raise ValueError('OAuth client must be a Desktop application')
    # Never accept configured token endpoints that could send credentials elsewhere.
    installed = config['installed']
    if (installed.get('auth_uri') != 'https://accounts.google.com/o/oauth2/auth' and
            installed.get('auth_uri') != 'https://accounts.google.com/o/oauth2/v2/auth'):
        raise ValueError('Unexpected Google authorization endpoint')
    if installed.get('token_uri') != 'https://oauth2.googleapis.com/token':
        raise ValueError('Unexpected Google token endpoint')
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        raise ValueError('Install optional requirements-youtube.txt in a virtual environment') from None
    try:
        flow = InstalledAppFlow.from_client_config(config, [SCOPE], autogenerate_code_verifier=True)
        creds = flow.run_local_server(host='127.0.0.1', port=port, open_browser=True,
                                      browser=browser, timeout_seconds=180,
                                      authorization_prompt_message='',
                                      success_message='Authorization received. Close this tab and return to the terminal.')
        scopes = creds.granted_scopes or creds.scopes
        if set(scopes or []) != {SCOPE}:
            raise ValueError('Unexpected OAuth scopes')
        private_write(folder / 'token.json', creds.to_json().encode())
    except Exception:
        # OAuth exceptions may contain callback codes, URLs or tokens.
        raise ResponseError('Google authorization did not finish. Check Desktop client, test user, '
                            'Windows browser and WSL localhost forwarding; rerun auth.') from None


class GoogleTransport:
    def __init__(self, folder):
        self.folder = outside_repo(folder)
        self.session = None

    def prepare(self):
        if self.session is None:
            token = outside_repo(self.folder / 'token.json')
            if not token.is_file():
                raise ResponseError('Google authorization required: run python -m pagefinder.local auth')
            try:
                from google.oauth2.credentials import Credentials
                from google.auth.transport.requests import AuthorizedSession
            except ImportError:
                raise ResponseError('Install optional requirements-youtube.txt first') from None
            config = json.loads(token.read_text(encoding='utf-8'))
            if not isinstance(config, dict) or config.get('token_uri') != 'https://oauth2.googleapis.com/token':
                raise ResponseError('Unexpected token endpoint; rerun auth')
            if set(config.get('scopes', [])) != {SCOPE}:
                raise ResponseError('Token scopes differ from youtube.readonly; rerun auth')
            self.creds = Credentials.from_authorized_user_info(config, [SCOPE])
            # Never let the SDK replay an API request outside the shared ledger.
            # Expired credentials can refresh before a request; a returned 401 stops.
            self.session = AuthorizedSession(self.creds, max_refresh_attempts=0, refresh_timeout=20)

    def __call__(self, url):
        self.prepare()
        try:
            res = self.session.get(url, timeout=20, allow_redirects=False)
            try:
                body = res.json()
            except ValueError:
                body = {'error': {'message': 'Non-JSON response'}}
            private_write(self.folder / 'token.json', self.creds.to_json().encode())
            return res.status_code, dict(res.headers), body
        except Exception:
            raise ResponseError('Google transport failed; credentials and response details withheld') from None


class YouTubeClient:
    def __init__(self, store, transport=None, *, offline=False, max_requests=100, daily_units=9000,
                 sleep=time.sleep, clock=time.time):
        self.store = store
        self.state = NetworkState(outside_repo(store.folder / 'http.sqlite3'), clock=clock)
        outside_repo(store.folder / 'http.sqlite3').chmod(0o600)
        self.transport = transport
        self.offline = offline
        if not 1 <= max_requests <= 1000 or not 1 <= daily_units <= 10000:
            raise ValueError('Request budget must be 1..1000; daily units must be 1..10000')
        self.max_requests, self.daily_units = max_requests, daily_units
        self.requests, self.cache_hits = 0, 0
        self.sleep = sleep

    def close(self):
        self.state.close()

    def get(self, resource, params, *, fresh_after=None):
        # This milestone intentionally cannot enumerate videos or playlist items.
        if resource != 'playlists' or params.get('mine') != 'true':
            raise ValueError('Only owned-playlist metadata is supported at this gate')
        url = BASE + resource + '?' + urlencode(sorted(params.items()))
        cached = self.state.cached(url)
        if cached and cached['status'] == 200 and (fresh_after is None or cached['fetched'] >= fresh_after):
            self.cache_hits += 1
            return cached
        if self.offline:
            raise ResponseError('Required playlist page is not cached; offline run stopped')
        if self.transport is None:
            raise ResponseError('No authorized transport configured')
        if hasattr(self.transport, 'prepare'):
            # Missing credentials/dependencies are not counted as API requests.
            self.transport.prepare()
        for attempt in range(3):
            if self.requests >= self.max_requests:
                raise BudgetExceeded('Batch request budget reached; progress saved for the next run')
            self.state.admit('youtube', interval=1.0, window=60, limit=60,
                             daily_units=self.daily_units, sleep=self.sleep)
            self.requests += 1
            try:
                status, headers, body = self.transport(url)
            except ResponseError:
                if attempt == 2:
                    raise
                self.sleep(2 ** attempt)
                continue
            if not isinstance(body, dict):
                raise ResponseError('Unexpected API response shape')
            self.state.save(url, status, headers, body)
            error = body.get('error') if isinstance(body.get('error'), dict) else {}
            errors = error.get('errors') if isinstance(error.get('errors'), list) else []
            reasons = {e.get('reason') for e in errors
                       if isinstance(e, dict)}
            self.state.response_limits('youtube', status, headers,
                                       quota_exhausted=bool(reasons & {'quotaExceeded', 'dailyLimitExceeded'}))
            if status == 200:
                return self.state.cached(url)
            if status in (403, 429):
                raise BudgetExceeded('YouTube refused the request (HTTP 403/429); cooldown saved, batch stopped')
            if status >= 500 and attempt < 2:
                self.sleep(2 ** attempt)
                continue
            raise ResponseError(f'YouTube returned HTTP {status}; response cached locally')


def inventory(store, client, *, refresh=False, max_pages=100):
    if not 1 <= max_pages <= 1000:
        raise ValueError('Page budget must be 1..1000')
    state = store.get_checkpoint('playlist_inventory')
    if refresh or state is None:
        previous = state
        state = {'started_at': now(), 'fresh_after': client.state.clock() if refresh else None,
                 'next_page': None, 'tokens': [], 'ids': [], 'pages': 0, 'complete': False}
        with store.db:
            if previous:
                store.checkpoint('playlist_inventory_previous', previous)
            store.checkpoint('playlist_inventory', state)
    try:
        if state['complete']:
            return state
        for _ in range(max_pages):
            params = {'part': 'snippet,contentDetails,status', 'mine': 'true', 'maxResults': 50}
            if state['next_page']:
                params['pageToken'] = state['next_page']
            response = client.get('playlists', params, fresh_after=state['fresh_after'])
            body = response['body']
            if not isinstance(body.get('items'), list):
                raise ResponseError('Playlist response has no items array; cached for inspection')
            next_page = body.get('nextPageToken')
            if next_page and (not isinstance(next_page, str) or next_page in state['tokens']):
                raise ResponseError('Repeated/invalid pagination token; stopped safely')
            with store.db:
                eid = store.evidence('youtube_playlist_inventory',
                                     'api-page:' + client.state.key(BASE + 'playlists?' + urlencode(sorted(params.items()))),
                                     retrieved_at=datetime.fromtimestamp(response['fetched'], timezone.utc).isoformat(),
                                     completeness='partial', notes={'scope': 'owned playlists, metadata only',
                                                                   'page': state['pages'] + 1})
                for item in body['items']:
                    if (not isinstance(item, dict) or not isinstance(item.get('id'), str) or
                            not re.fullmatch(r'[A-Za-z0-9_-]+', item['id'])):
                        raise ResponseError('Playlist without a stable ID; page not committed')
                    pid = 'youtube:playlist:' + item['id']
                    snippet, details = item.get('snippet', {}), item.get('contentDetails', {})
                    status = item.get('status', {})
                    if (not all(isinstance(value, dict) for value in (snippet, details, status)) or
                            not all(isinstance(snippet.get(k, ''), str) for k in
                                    ('title', 'description', 'channelId')) or
                            status.get('privacyStatus', 'unknown') not in ('private', 'unlisted', 'public', 'unknown') or
                            (details.get('itemCount') is not None and
                             (type(details['itemCount']) is not int or details['itemCount'] < 0))):
                        raise ResponseError('Malformed playlist metadata; page not committed')
                    owner = snippet.get('channelId')
                    bound_owner = store.get_checkpoint('youtube_owner')
                    if owner and bound_owner and owner != bound_owner:
                        raise ResponseError('Different YouTube owner detected; use a separate private data directory')
                    if owner and not bound_owner:
                        store.checkpoint('youtube_owner', owner)
                    store.entity(pid, 'youtube_playlist', item['id'], snippet.get('title', ''), eid,
                                 url='https://www.youtube.com/playlist?' + urlencode({'list': item['id']}),
                                 creator_id=snippet.get('channelId'), published_at=snippet.get('publishedAt'))
                    store.checkpoint('playlist_metadata:' + pid,
                                     {'description': snippet.get('description', ''),
                                      'privacy': status.get('privacyStatus', 'unknown'),
                                      'count': details.get('itemCount'), 'retrieved_at': response['fetched']})
                    if pid not in state['ids']:
                        state['ids'].append(pid)
                state['pages'] += 1
                state['next_page'] = next_page
                if next_page:
                    state['tokens'].append(next_page)
                state['complete'] = not next_page
                store.checkpoint('playlist_inventory', state)
            if state['complete']:
                with store.db:
                    store.evidence('youtube_playlist_inventory_run', state['started_at'],
                                   completeness='complete_for_request', notes={
                                       'playlists': len(state['ids']), 'pages': state['pages'],
                                       'limitations': 'Accessible owned playlists at retrieval time; system collections excluded.'})
                break
        return state
    finally:
        # Include partial progress and quotas even if a later page failed.
        write_inventory(store, client)


def inventory_rows(store):
    state = store.get_checkpoint('playlist_inventory', {'ids': []})
    rows = []
    for pid in state['ids']:
        entity = store.db.execute('SELECT * FROM entities WHERE id=?', (pid,)).fetchone()
        annotation = store.db.execute('SELECT * FROM playlist_annotations WHERE playlist_id=?', (pid,)).fetchone()
        rows.append({'id': entity['native_id'], 'title': entity['title'],
                     **store.get_checkpoint('playlist_metadata:' + pid, {}),
                     'purpose': annotation['purpose'] if annotation else 'unknown',
                     'relevance': annotation['relevance'] if annotation else 'unknown',
                     'notes': annotation['notes'] if annotation else '',
                     'reviewed': bool(annotation['reviewed']) if annotation else False})
    return rows


def write_inventory(store, client=None):
    rows = inventory_rows(store)
    if client:
        with store.db:
            store.checkpoint('inventory_last_invocation',
                             {'api_attempts': client.requests, 'cache_hits': client.cache_hits})
            store.checkpoint('inventory_budget_usage', client.state.usage())
    report = {'version': 1, 'visibility': 'private', 'playlists': rows,
              'checkpoint': store.get_checkpoint('playlist_inventory'), 'system_collections': SYSTEM_COLLECTIONS,
              'last_invocation': store.get_checkpoint('inventory_last_invocation'),
              'budget_usage': store.get_checkpoint('inventory_budget_usage'),
              'next_action': 'Review purposes/relevance before choosing any playlist content imports.'}
    private_json(store.folder / 'playlist_inventory.json', report)
    buf = io.StringIO(newline='')
    columns = ['id', 'title', 'privacy', 'count', 'description', 'purpose', 'relevance', 'notes', 'reviewed']
    writer = csv.DictWriter(buf, fieldnames=columns, extrasaction='ignore')
    writer.writeheader()
    for row in rows:
        # Avoid spreadsheet formulas from remote titles/descriptions.
        writer.writerow({k: ("'" + str(v) if isinstance(v, str) and v.lstrip().startswith(('=', '+', '-', '@'))
                             else v) for k, v in row.items()})
    private_write(store.folder / 'playlist_inventory.csv', buf.getvalue().encode())
    body = []
    def select(name, choices, value):
        return '<select data-field="' + name + '">' + ''.join(
            '<option' + (' selected' if c == value else '') + '>' + c + '</option>' for c in choices) + '</select>'
    for r in rows:
        h = lambda x: html.escape(str(x if x is not None else 'unknown'), quote=True)
        body.append('<tr data-id="' + h(r['id']) + '"><td><strong>' + h(r['title']) + '</strong><br>' +
                    h(r['id']) + '<details><summary>Description</summary>' + h(r['description']) +
                    '</details></td><td>' + h(r['privacy']) + '</td><td>' + h(r['count']) + '</td><td>' +
                    select('purpose', PURPOSES, r['purpose']) + '</td><td>' +
                    select('relevance', RELEVANCE, r['relevance']) + '</td><td><input data-field="notes" value="' +
                    h(r['notes']) + '" aria-label="Notes"></td><td><input type="checkbox" data-field="reviewed" ' +
                    ('checked ' if r['reviewed'] else '') + 'aria-label="Reviewed"></td></tr>')
    page = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'none'; img-src 'none'; base-uri 'none'; form-action 'none'">
<title>Private playlist inventory</title><style>
body{font:16px system-ui;background:#fafbfc;color:#172b40;margin:2rem}table{border-collapse:collapse;width:100%;background:white}
th,td{padding:.8rem;border-bottom:1px solid #dde3e9;text-align:left;vertical-align:top}input,select,button{font:inherit;padding:.4rem}
button{margin:1rem 0}details{max-width:32rem;white-space:pre-wrap}p{max-width:80ch}</style>
<h1>Private playlist inventory</h1><p>Metadata only. A queue means intent; saved does not mean watched.
Choose each playlist's purpose and relevance, mark it reviewed, then download annotations.
Edits remain in this tab until downloaded; apply the file with the local annotate command.</p>
<p id="coverage"></p><label>Filter <input id="filter" type="search"></label>
<button id="save">Download annotations</button><table><thead><tr><th>Playlist</th><th>Privacy</th><th>Items</th>
<th>Purpose</th><th>Relevance</th><th>Notes</th><th>Reviewed</th></tr></thead><tbody>''' + ''.join(body) + '''</tbody></table>
<p>Likes: separate API, latest 1,000 maximum. Watch Later and History: Takeout only. No system collections fetched.</p>
<script>
const rows=[...document.querySelectorAll('tbody tr')];
document.querySelector('#coverage').textContent=SUMMARY;
document.querySelector('#filter').addEventListener('input',e=>{for(const r of rows)r.hidden=!r.textContent.toLowerCase().includes(e.target.value.toLowerCase())});
document.querySelector('#save').addEventListener('click',()=>{
const playlists=rows.map(r=>{const v={id:r.dataset.id};for(const f of r.querySelectorAll('[data-field]'))v[f.dataset.field]=f.type==='checkbox'?f.checked:f.value;return v});
const blob=new Blob([JSON.stringify({version:1,playlists},null,2)],{type:'application/json'});
const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='playlist_annotations.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);
});</script></html>'''
    state = report['checkpoint'] or {}
    summary = f"{len(rows)} playlists; {state.get('pages', 0)} pages; " + (
        'complete for this owned-playlist request.' if state.get('complete') else 'partial inventory; resume required.')
    page = page.replace('textContent=SUMMARY;', 'textContent=' + json.dumps(summary) + ';')
    private_write(store.folder / 'playlist_inventory.html', page.encode())
    private_json(store.folder / 'evidence_coverage.json', store.coverage())


def annotate(store, path):
    path = outside_repo(path)
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('playlists'), list):
        raise ValueError('Expected version 1 playlist annotations JSON')
    known = {r['id'] for r in inventory_rows(store)}
    seen = set()
    with store.db:
        eid = store.evidence('manual_playlist_annotation', str(path))
        for row in data['playlists']:
            if not isinstance(row, dict):
                raise ValueError('Annotation rows must be objects')
            pid = row.get('id')
            if not isinstance(pid, str) or pid not in known or pid in seen:
                raise ValueError('Unknown or duplicate playlist ID in annotations')
            seen.add(pid)
            if row.get('purpose') not in PURPOSES or row.get('relevance') not in RELEVANCE:
                raise ValueError('Unsupported purpose/relevance label')
            if not isinstance(row.get('reviewed'), bool) or not isinstance(row.get('notes', ''), str):
                raise ValueError('Invalid annotation field type')
            if row['reviewed'] and row['purpose'] == 'unknown':
                raise ValueError('Reviewed playlists need an explicit purpose')
            store.db.execute('INSERT INTO playlist_annotations VALUES (?,?,?,?,?,?,?) '
                             'ON CONFLICT(playlist_id) DO UPDATE SET purpose=excluded.purpose,'
                             'relevance=excluded.relevance,notes=excluded.notes,reviewed=excluded.reviewed,'
                             'updated_at=excluded.updated_at,evidence_id=excluded.evidence_id',
                             ('youtube:playlist:' + pid, row['purpose'], row['relevance'], row.get('notes', ''),
                              int(row['reviewed']), now(), eid))
    # Snapshot the actual reviewed inputs; future recomputations cannot overwrite them.
    from .research import stable_id
    private_json(store.folder / 'annotations' / (stable_id(data) + '.json'), data)
    write_inventory(store)
    return len(seen)
