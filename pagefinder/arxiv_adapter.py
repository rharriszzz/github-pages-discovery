"""Read-only adapter for arXiv Shelf's schema-1 append-only event catalog.

Mirrors catalog.Catalog.read_state(): collect aliases from every ordered event
first, then merge metadata/filenames and apply the last rating (including zero).
Never imports Shelf, starts a scanner, executes its code or writes to its tree.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

ARXIV_ID = re.compile(r'^(?:\d{4}\.\d{4,5}|[a-z][a-z.-]*(?:\.[A-Z]{2})?/\d{7})(?:v[1-9]\d*)?$', re.I)


def read_catalog(directory):
    directory = Path(directory).expanduser().resolve()
    catalog = directory / 'catalog'
    if not catalog.is_dir():
        raise FileNotFoundError('arXiv Shelf catalog is unavailable')
    files = sorted(catalog.glob('*.json'))
    if len(files) > 10000 or sum(p.stat().st_size for p in files) > 50_000_000:
        raise ValueError('arXiv Shelf catalog exceeds the local read bound')
    events, digests = [], []
    for path in files:
        raw = path.read_bytes()
        event = json.loads(raw)
        if not isinstance(event, dict) or event.get('schema') != 1:
            raise ValueError('Unsupported arXiv Shelf event schema')
        if not isinstance(event.get('time'), (int, float)) or not isinstance(event.get('id'), str):
            raise ValueError('Invalid arXiv Shelf event identity')
        events.append(event)
        digests.append(hashlib.sha256(raw).hexdigest())
    events.sort(key=lambda e: (e['time'], e['id']))
    aliases, papers, ratings = {}, {}, {}
    for event in events:
        aliases.update(event.get('aliases', {}))
    for event in events:
        for key, paper in event.get('papers', {}).items():
            key = aliases.get(key, key)
            old = papers.get(key, {})
            names = sorted(set(old.get('filenames', []) + paper.get('filenames', [])))
            papers[key] = {**old, **paper, 'filenames': names}
        for key, rating in event.get('ratings', {}).items():
            if type(rating) is not int or not 0 <= rating <= 5:
                raise ValueError('Invalid arXiv Shelf star rating')
            ratings[aliases.get(key, key)] = rating
    for key, paper in papers.items():
        paper['catalog_key'] = key
        paper['rating'] = ratings.get(key, 0)
    return papers, aliases, hashlib.sha256(''.join(digests).encode()).hexdigest()


def verified_local_ids(directory):
    """Use Shelf's own cache as a hint; confirm a contained file with a PDF header.

    No absolute paths or filenames escape this function. A miss means unverified,
    not absent everywhere. Opening uses arxiv.org, never Shelf's protected route.
    """
    try:
        path = Path(directory).expanduser().resolve() / '.shelf/index.json'
        if path.stat().st_size > 20_000_000:
            return set()
        cache = json.loads(path.read_text())
        root = Path(cache['directory']).expanduser().resolve(strict=True)
        available = set()
        for row in cache.get('papers', []):
            identifier = row.get('arxiv_id', '')
            if not isinstance(identifier, str) or not ARXIV_ID.fullmatch(identifier) or not row.get('valid_pdf'):
                continue
            try:
                candidate = Path(row.get('path', '')).resolve(strict=True)
                if candidate.is_relative_to(root) and candidate.is_file() and candidate.suffix.lower() == '.pdf':
                    with candidate.open('rb') as handle:
                        if handle.read(5) == b'%PDF-':
                            available.add(identifier)
            except (OSError, ValueError, TypeError):
                continue
        return available
    except (OSError, ValueError, KeyError, TypeError):
        return set()


def load_shelf(directory):
    papers, aliases, fingerprint = read_catalog(directory)
    local = verified_local_ids(directory)
    result, unresolved = {}, 0
    for key, paper in papers.items():
        identifier = paper.get('arxiv_id')
        if not isinstance(identifier, str) or not ARXIV_ID.fullmatch(identifier) or not paper.get('title'):
            unresolved += 1
            continue
        version = re.search(r'v(\d+)$', identifier, re.I)
        url = 'https://arxiv.org/abs/' + identifier
        result[identifier] = {'title': paper['title'], 'url': url, 'kind': 'paper',
            'authors': paper.get('authors', []), 'abstract': paper.get('abstract', ''),
            'published': paper.get('published', ''), 'arxiv_id': identifier,
            'arxiv_base': re.sub(r'v\d+$', '', identifier, flags=re.I),
            'arxiv_version': int(version[1]) if version else None,
            'star_rating': paper['rating'] or None, 'catalog_key': key,
            'pdf_status': 'verified_local' if identifier in local else 'not_verified',
            'pdf_url': 'https://arxiv.org/pdf/' + identifier,
            'origins': ['Your arXiv Shelf'], 'source': 'shelf',
            'summary': '', 'topics': [], 'evidence': [{'url': url,
                'note': 'Title, authors and abstract from the read-only portable Shelf catalog; not a full-paper assessment.'}],
            'evidence_level': 'catalog_metadata', 'duration_seconds': None,
            'limitations': ['Collection membership and stars do not establish reading or completion.',
                             'Local PDF presence is a separate file check; unverified does not mean unavailable everywhere.']}
    return list(result.values()), {'status': 'ready', 'papers': len(result),
        'unresolved': unresolved, 'aliases': len(aliases), 'fingerprint': fingerprint,
        'rated': sum(bool(p['star_rating']) for p in result.values()),
        'local_pdfs_verified': sum(p['pdf_status'] == 'verified_local' for p in result.values())}
