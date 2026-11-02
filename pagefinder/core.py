"""Conservative GitHub Pages discovery, evidence gathering and ranking.

Standard library only. No authentication token is written to disk or logs.
"""
from __future__ import annotations

import hashlib
import html
import io
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.robotparser import RobotFileParser
from .net import BudgetExceeded, NetworkState

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / 'data' / 'sites.json'
USER_AGENT = 'GithubPagesInterestFinder/0.1 (research; low-rate; public pages only)'
HOST_RE = re.compile(r'^[a-z0-9](?:[a-z0-9-]{0,37}[a-z0-9])?\.github\.io$', re.I)
MAX_HTML_BYTES = 300_000


class ApiError(Exception):
    pass


class RateLimited(ApiError):
    pass


class GitHubRedirects(HTTPRedirectHandler):
    max_redirections = 3

    def __init__(self, admit):
        self.admit = admit

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urlsplit(newurl)
        if (parsed.scheme != 'https' or parsed.hostname != 'api.github.com' or
                parsed.username or parsed.password or parsed.port):
            raise ApiError('GitHub redirect outside the API was not followed')
        self.admit(parsed.path)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def load_json(path: Path, fallback):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else fallback


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + '\n', encoding='utf-8')
    temp.replace(path)


def safe_site(url: str) -> str | None:
    try:
        p = urlsplit(url)
        if p.scheme != 'https' or not p.hostname or not HOST_RE.fullmatch(p.hostname):
            return None
        if p.username or p.password or p.port or p.fragment or p.query:
            return None
        if any(seg in ('.', '..') for seg in p.path.split('/')):
            return None
        return p.geturl()
    except ValueError:
        return None


def github_token():
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if token:
        return token.strip()
    try:
        proc = subprocess.run(['gh', 'auth', 'token'], capture_output=True, text=True,
                              timeout=4, check=False)
        if proc.returncode == 0:
            return proc.stdout.strip() or None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


class GitHubClient:
    def __init__(self, delay: float = 2.1, offline: bool = False, cache_days: int = 7):
        self.token = github_token()
        self.delay = max(0, delay)
        self.offline = offline
        self.cache_days = cache_days
        self.last_request = 0.0
        self.cache_dir = ROOT / '.cache' / 'github'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.network = NetworkState(ROOT / '.cache' / 'http.sqlite3')

    def _admit(self, path):
        try:
            if path.startswith('/search/'):
                self.network.admit('github_search', interval=max(self.delay, 6.1), window=60, limit=10)
            self.network.admit('github_core', interval=max(self.delay, 1.0), window=3600,
                               limit=5000 if self.token else 60)
        except BudgetExceeded as exc:
            raise RateLimited(str(exc)) from None

    def get(self, path: str, params: dict | None = None):
        url = 'https://api.github.com' + path
        if params:
            url += '?' + urlencode(params)
        key = hashlib.sha256(url.encode()).hexdigest()
        fp = self.cache_dir / f'{key}.json'
        cached = self.network.cached(url)
        if cached and cached['status'] == 200 and (self.offline or
                time.time() - cached['fetched'] < self.cache_days * 86400):
            return cached['body']
        if fp.exists() and (self.offline or time.time() - fp.stat().st_mtime < self.cache_days * 86400):
            return load_json(fp, {})
        if self.offline:
            raise ApiError(f'Not cached (offline): {path}')
        # Search shares core accounting; redirects also pass through admission.
        self._admit(path)
        wait = self.delay - (time.monotonic() - self.last_request)
        if wait > 0:
            time.sleep(wait)
        headers = {'Accept': 'application/vnd.github+json', 'User-Agent': USER_AGENT,
                   'X-GitHub-Api-Version': '2022-11-28'}
        if self.token:
            headers['Authorization'] = 'Bearer ' + self.token
        try:
            with build_opener(GitHubRedirects(self._admit)).open(Request(url, headers=headers), timeout=20) as res:
                self.last_request = time.monotonic()
                body = res.read(2_000_000)
                data = json.loads(body)
                self.network.save(url, res.status, dict(res.headers), data)
                self.network.response_limits('github_core', res.status, dict(res.headers))
                if path.startswith('/search/'):
                    self.network.response_limits('github_search', res.status, dict(res.headers))
                save_json(fp, data)
                return data
        except HTTPError as e:
            self.last_request = time.monotonic()
            try:
                error_body = json.loads(e.read(100_000))
            except (ValueError, OSError):
                error_body = {'error': 'Unparseable error response'}
            finally:
                e.close()
            self.network.save(url, e.code, dict(e.headers), error_body)
            self.network.response_limits('github_core', e.code, dict(e.headers))
            if path.startswith('/search/'):
                self.network.response_limits('github_search', e.code, dict(e.headers))
            remaining = e.headers.get('X-RateLimit-Remaining', '?')
            reset = e.headers.get('X-RateLimit-Reset', '?')
            retry = e.headers.get('Retry-After', '?')
            if e.code in (403, 429):
                raise RateLimited(f'GitHub returned {e.code}; remaining={remaining}, reset={reset}, '
                                  f'retry-after={retry}. Stopped; do not repeatedly retry.') from e
            raise ApiError(f'GitHub returned HTTP {e.code} for {path}') from e
        except (URLError, TimeoutError) as e:
            raise ApiError(f'GitHub request failed: {e}') from e


def repo_site_urls(repo: dict) -> list[str]:
    """Potential Pages URLs; existence must subsequently be checked via HTTP."""
    owner = repo.get('owner') or {}
    login = (owner.get('login') or '').lower()
    name = (repo.get('name') or '').lower()
    if not login or not name or not HOST_RE.fullmatch(login + '.github.io'):
        return []
    urls = []
    if name == login + '.github.io':
        urls.append(f'https://{login}.github.io/')
    if repo.get('has_pages') and name != login + '.github.io':
        urls.append(f'https://{login}.github.io/{quote(name, safe="-")}/')
    homepage = repo.get('homepage') or ''
    if safe_site(homepage):
        urls.insert(0, homepage)
    return list(dict.fromkeys(urls))


def record_from_repo(repo: dict, site_url: str, discovered_by: str) -> dict:
    owner = repo.get('owner') or {}
    return dict(url=site_url, owner=owner.get('login', ''), account_type=owner.get('type', 'Unknown'),
                account_type_source='GitHub repository owner.type',
                repository=repo.get('full_name', ''), repo_url=repo.get('html_url', ''),
                repo_description=repo.get('description') or '',
                topics=repo.get('topics') or [], language=repo.get('language') or '',
                stars=repo.get('stargazers_count', 0), updated_at=repo.get('updated_at', ''),
                source=discovered_by, site_status='unchecked', title='', summary='', body='')


def discover(queries: list[str], limit_per_query: int = 100, pages_per_query: int = 1,
             offline: bool = False, delay: float = 2.1):
    client = GitHubClient(delay=delay, offline=offline)
    rows = load_json(DB, [])
    by_url = {r['url']: r for r in rows}
    stats = []
    for query in queries:
        count, matched, truncated = 0, 0, False
        for page in range(1, pages_per_query + 1):
            try:
                result = client.get('/search/repositories', {'q': query, 'per_page': min(limit_per_query, 100),
                                                               'page': page})
            except RateLimited:
                save_json(DB, sorted(by_url.values(), key=lambda r: r['url']))
                raise
            repos = result.get('items') or []
            count += len(repos)
            for repo in repos:
                for url in repo_site_urls(repo):
                    matched += 1
                    new = record_from_repo(repo, url, 'GitHub repository search: ' + query)
                    if url in by_url:
                        # Preserve downloaded site text and manual review fields.
                        by_url[url] = {**by_url[url], **{k: v for k, v in new.items()
                                      if k not in ('title', 'summary', 'body', 'site_status', 'review')}}
                    else:
                        by_url[url] = new
            if len(repos) < min(limit_per_query, 100):
                break
            if page == pages_per_query and result.get('total_count', 0) > page * min(limit_per_query, 100):
                truncated = True
        stats.append({'query': query, 'repositories_examined': count,
                      'candidate_sites': matched, 'truncated': truncated})
        save_json(DB, sorted(by_url.values(), key=lambda r: r['url']))
    return stats


class PageText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.in_title = False
        self.title_parts = []
        self.text_parts = []
        self.description = ''

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('script', 'style', 'noscript', 'svg'):
            self.skip += 1
        if tag == 'title':
            self.in_title = True
        if tag == 'meta' and attrs.get('name', '').lower() == 'description':
            self.description = attrs.get('content', '')[:500]

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript', 'svg'):
            self.skip = max(0, self.skip - 1)
        if tag == 'title':
            self.in_title = False

    def handle_data(self, data):
        data = ' '.join(data.split())
        if not data or self.skip:
            return
        if self.in_title:
            self.title_parts.append(data)
        self.text_parts.append(data)


class NoExternalRedirects(HTTPRedirectHandler):
    max_redirections = 3

    def __init__(self, before_redirect=None):
        self.before_redirect = before_redirect

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not safe_site(newurl):
            raise HTTPError(newurl, code, 'Non-GitHub-Pages redirect not followed', headers, fp)
        if self.before_redirect:
            self.before_redirect(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class PageFetcher:
    def __init__(self, delay: float = 1.0, offline: bool = False):
        self.delay, self.offline = delay, offline
        self.network = NetworkState(ROOT / '.cache' / 'http.sqlite3')
        self.opener = build_opener(NoExternalRedirects(self._reserve))
        self.last = 0.0
        self.robots = {}
        self.cache_dir = ROOT / '.cache' / 'pages'
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch(self, url: str) -> dict:
        result = self._fetch(url)
        if safe_site(url):
            key = hashlib.sha256(url.encode()).hexdigest()
            # Include failures rather than silently forgetting excluded candidates.
            path = self.cache_dir / (key + '.json')
            if result.get('site_status') != 'not_cached' and (not path.exists() or
                    load_json(path, {}) != result or time.time() - path.stat().st_mtime >= 2 * 86400):
                save_json(path, result)
        return result

    def _reserve(self, url):
        try:
            self.network.admit('sites_global', interval=max(self.delay, 1.0), window=3600, limit=500)
            self.network.admit('site:' + str(urlsplit(url).hostname),
                               interval=max(self.delay, 2.0), window=3600, limit=100)
        except BudgetExceeded as exc:
            raise RateLimited(str(exc)) from None

    def _open(self, url, limit, timeout):
        # Cache raw bounded responses for reproducibility, including robots and errors.
        cached = self.network.cached(url)
        if cached and time.time() - cached['fetched'] < 2 * 86400:
            raw = cached['body']['raw'].encode()
            if cached['status'] != 200:
                raise HTTPError(url, cached['status'], 'Cached response', cached['headers'], io.BytesIO(raw))
            return raw, cached['headers']
        self._reserve(url)
        try:
            res = self.opener.open(Request(url, headers={'User-Agent': USER_AGENT,
                                                        'Accept': 'text/html,text/plain'}), timeout=timeout)
        except HTTPError as exc:
            self.network.save(url, exc.code, dict(exc.headers),
                              {'raw': exc.read(min(limit, 100_000)).decode('utf-8', 'replace')})
            self.network.response_limits('site:' + str(urlsplit(url).hostname), exc.code, dict(exc.headers))
            self.network.response_limits('sites_global', exc.code, dict(exc.headers))
            raise
        with res:
            raw = res.read(limit + 1)
            self.network.save(url, res.status, dict(res.headers), {'raw': raw.decode('utf-8', 'replace')})
            self.network.response_limits('site:' + str(urlsplit(url).hostname), res.status, dict(res.headers))
            return raw, res.headers

    def _fetch(self, url: str) -> dict:
        if not safe_site(url):
            return {'site_status': 'rejected_url'}
        key = hashlib.sha256(url.encode()).hexdigest()
        fp = self.cache_dir / (key + '.json')
        if fp.exists() and (self.offline or time.time() - fp.stat().st_mtime < 2 * 86400):
            return load_json(fp, {})
        if self.offline:
            return {'site_status': 'not_cached'}
        host = urlsplit(url).hostname
        if host not in self.robots:
            rp = RobotFileParser()
            robots_url = f'https://{host}/robots.txt'
            try:
                self._delay()
                raw, _ = self._open(robots_url, 40_000, 12)
                rp.parse(raw.decode('utf-8', 'replace').splitlines())
            except HTTPError as e:
                if e.code == 404:
                    rp.parse([])
                else:
                    self.robots[host] = None
                    return {'site_status': f'robots_http_{e.code}'}
            except (URLError, TimeoutError):
                self.robots[host] = None
                return {'site_status': 'robots_unavailable'}
            self.robots[host] = rp
        if self.robots[host] is None:
            return {'site_status': 'robots_unavailable'}
        if not self.robots[host].can_fetch(USER_AGENT, url):
            return {'site_status': 'robots_disallowed'}
        try:
            self._delay()
            raw, headers = self._open(url, MAX_HTML_BYTES, 18)
            if 'text/html' not in (headers.get('Content-Type') or headers.get('content-type', '')).lower():
                return {'site_status': 'non_html'}
            if len(raw) > MAX_HTML_BYTES:
                return {'site_status': 'too_large'}
            parser = PageText()
            parser.feed(raw.decode('utf-8', 'replace'))
            data = dict(site_status='ok', title=' '.join(parser.title_parts)[:200],
                        summary=parser.description, body=' '.join(parser.text_parts)[:12_000])
            save_json(fp, data)
            return data
        except HTTPError as e:
            return {'site_status': f'http_{e.code}'}
        except (URLError, TimeoutError, UnicodeError, ValueError):
            return {'site_status': 'fetch_failed'}

    def _delay(self):
        wait = self.delay - (time.monotonic() - self.last)
        if wait > 0:
            time.sleep(wait)
        self.last = time.monotonic()


def enrich(max_sites: int = 50, offline: bool = False, refresh_owners: bool = True,
           request_delay: float = 2.1):
    rows = load_json(DB, [])
    api = GitHubClient(delay=request_delay, offline=offline)
    fetcher = PageFetcher(offline=offline)
    updated = 0
    for r in rows:
        if updated >= max_sites:
            break
        if r.get('site_status') == 'ok' and r.get('account_type') in ('User', 'Organization'):
            continue
        if refresh_owners and r.get('owner'):
            try:
                profile = api.get('/users/' + quote(r['owner']))
                r['account_type'] = profile.get('type', 'Unknown')
                r['account_type_source'] = 'GitHub GET /users/{owner} type'
            except RateLimited:
                save_json(DB, rows)
                raise
            except ApiError:
                pass
        r.update(fetcher.fetch(r['url']))
        updated += 1
        save_json(DB, rows)  # checkpoint after each candidate
    return updated


def score(row: dict, interests: list[dict]):
    findings = []
    total = 0
    for topic in interests:
        matches = []
        for term in topic['terms']:
            regex = re.compile(r'(?<!\w)' + re.escape(term.lower()) + r'(?!\w)', re.I)
            evidence = []
            for field, label in [('title', 'title'), ('summary', 'description'),
                                 ('repo_description', 'repository'), ('body', 'site'),
                                 ('topics', 'repo topic')]:
                val = row.get(field) or ''
                if isinstance(val, list):
                    val = ' '.join(val)
                if regex.search(val):
                    evidence.append(label)
            if evidence:
                matches.append({'term': term, 'evidence': evidence})
        if matches:
            # One distinctive term is useful, multiple independent terms are stronger.
            points = min(26, 8 + 6 * min(3, len(matches) - 1) +
                         (4 if any('title' in m['evidence'] for m in matches) else 0))
            points = int(points * topic['weight'] / 5)
            total += points
            findings.append({'topic': topic['name'], 'points': points, 'matches': matches})
    findings.sort(key=lambda x: -x['points'])
    return {'score': min(total, 100), 'interests': [f['topic'] for f in findings],
            'evidence': findings}


def rank_all(profile_path: Path = ROOT / 'data' / 'interests.json'):
    profile = load_json(profile_path, {})
    return sorted([{**r, **score(r, profile['interests'])} for r in load_json(DB, [])],
                   key=lambda r: (-r['score'], r['url']))
