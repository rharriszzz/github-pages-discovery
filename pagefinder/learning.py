"""Private work-level Learning Queue, local retrieval and independent feedback.

No network requests. Source refresh reads local catalogs/checkpoints only. Work
metadata is an additive index; all old evidence and creator reviews remain intact.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit, urlunsplit

from .arxiv_adapter import load_shelf
from .creators import creator_report, safe_url
from .privacy import outside_repo, private_json, private_write
from .research import now

KINDS = ('paper', 'video', 'code', 'article', 'demo')
GOALS = ('', 'overview', 'deep', 'revisit', 'adjacent')
TIMES = ('', 'short', 'medium', 'substantial')
FORMATS = ('', 'watch', 'read', 'code')
STOP = set('a about an and are as at be best better can could do does explain find for from good how i in into is it know learn learning me my of on or please should some that the their this to understand understanding useful want way what when which why with would you your'.split())
ALIASES = {'fluids': 'fluid', 'simulations': 'simulation', 'simulating': 'simulation',
           'othello': 'reversi',
           'vortices': 'vortex', 'rendering': 'render', 'renders': 'render', 'renderer': 'render',
           'numerics': 'numerical', 'geometrical': 'geometry', 'geometric': 'geometry',
           'transcribing': 'transcription', 'evaluating': 'evaluation', 'stabilization': 'stability',
           'algorithms': 'algorithm', 'methods': 'method', 'tensors': 'tensor', 'spinors': 'spinor'}


def tokens(text):
    return {ALIASES.get(t, t) for t in re.findall(r'[a-z0-9]+', text.lower()) if len(t) > 1 and t not in STOP}


def canonical_url(url):
    if not safe_url(url):
        raise ValueError('Learning resources need credential-free HTTPS links')
    p = urlsplit(url)
    if p.hostname in ('localhost', '127.0.0.1', '::1') or p.port:
        raise ValueError('Learning links must be external HTTPS sources')
    if p.hostname in ('youtube.com', 'www.youtube.com', 'youtu.be'):
        identifier = p.path.strip('/') if p.hostname == 'youtu.be' else parse_qs(p.query).get('v', [''])[0]
        if p.path.startswith(('/live/', '/shorts/')):
            identifier = p.path.split('/')[2]
        if re.fullmatch(r'[\w-]{11}', identifier):
            return 'https://www.youtube.com/watch?v=' + identifier
    if p.hostname in ('github.com', 'www.github.com'):
        pieces = p.path.rstrip('/').split('/')
        pieces[:3] = [v.lower() for v in pieces[:3]]
        return urlunsplit(('https', 'github.com', '/'.join(pieces), p.query, p.fragment))
    return urlunsplit(('https', p.hostname, p.path.rstrip('/'), p.query, p.fragment))


def work_id(url):
    return 'learning:' + hashlib.sha256(canonical_url(url).encode()).hexdigest()


def _cites_work(work, source):
    if canonical_url(work) == canonical_url(source):
        return True
    a, b = urlsplit(work), urlsplit(source)
    if a.hostname != 'github.com' or b.hostname != 'github.com':
        return False
    x, y = a.path.strip('/').split('/'), b.path.strip('/').split('/')
    if [p.lower() for p in x[:2]] != [p.lower() for p in y[:2]]:
        return False
    if len(x) == 2:
        return True
    # A tree and its cited blob share the repo-relative path despite different
    # URL markers. A root citation alone doesn't qualify every subproject.
    return (len(x) > 4 and len(y) > 4 and x[2] in ('tree', 'blob') and
            y[2] in ('tree', 'blob') and y[4:4 + len(x[4:])] == x[4:])


def initialize(store):
    # Feature-owned additive tables leave schema-v1 entities/reviews unchanged.
    store.db.executescript('''
        CREATE TABLE IF NOT EXISTS learning_works (
            id TEXT PRIMARY KEY REFERENCES entities(id), payload TEXT NOT NULL,
            digest TEXT NOT NULL, updated_at TEXT NOT NULL, active INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS learning_feedback (
            work_id TEXT PRIMARY KEY REFERENCES learning_works(id),
            saved INTEGER NOT NULL DEFAULT 0, completed INTEGER NOT NULL DEFAULT 0,
            useful INTEGER, notes TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL,
            evidence_id TEXT NOT NULL REFERENCES evidence(id));
    ''')


def _load_json(path, bound=20_000_000):
    path = outside_repo(path)
    if path.stat().st_size > bound:
        raise ValueError('Private learning input exceeds its size bound')
    return json.loads(path.read_text())


def _duration(item):
    duration = item.get('contentDetails', {}).get('duration', '')
    m = re.fullmatch(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    return sum(int(v or 0) * unit for v, unit in zip(m.groups(), (3600, 60, 1))) if m else None


def _discovery(store):
    works = []
    report = creator_report(store)
    metadata = store.get_checkpoint('creator_metadata', {}).get('videos', {})
    for row in report['investigated']:
        if not row.get('recommend'):
            continue
        for family in ('videos', 'projects'):
            for item in row.get(family, []):
                url = canonical_url(item['url'])
                video = 'youtube.com/watch?' in url
                vid = parse_qs(urlsplit(url).query).get('v', [''])[0]
                meta = metadata.get(vid, {}).get('item', {})
                linked_concepts = [c for c in row.get('learning_concepts', []) if any(
                    _cites_work(url, u)
                    for u in c.get('sources', []))]
                works.append({'url': url, 'title': item['title'],
                    'kind': 'video' if video else 'code' if urlsplit(url).hostname == 'github.com' else 'article',
                    'authors': [row['name']], 'creator_ids': [row['id']],
                    'origins': ['Earlier creator research'], 'source': 'discovery',
                    'summary': item['note'], 'abstract': '',
                    'description': meta.get('snippet', {}).get('description', '')[:4000],
                    'topics': [c['label'] for c in linked_concepts],
                    'bridges': [{'label': c['label'], 'terms': [c['label']],
                        'explanation': c['explanation'], 'sources': c['sources']}
                        for c in linked_concepts],
                    'creator_topics': row.get('subjects', []) + row.get('methods', []),
                    'concepts': row.get('learning_concepts', []),
                    'creator_review': row['review']['decision'],
                    'duration_seconds': _duration(meta),
                    'evidence_level': 'earlier_work_notes',
                    'evidence': [{'url': item.get('source_url', item['url']),
                        'retrieved_at': item.get('retrieved_at'), 'note': item['note']}],
                    'limitations': ['Earlier bounded creator research; full work not necessarily inspected.',
                                    'Creator feedback is distinct from feedback on this work.']})
    # Saved bookmarks are encounter evidence, not implicit recommendations.
    # They can be found by title; they receive no curated-evidence boost.
    path = store.folder / 'bookmark_inventory.json'
    if path.exists():
        for row in _load_json(path).get('bookmarks', []):
            url = row.get('url')
            if not url or not safe_url(url):
                continue
            try:
                canonical_url(url)
            except ValueError:
                continue
            works.append({'url': url, 'title': row.get('title') or row.get('name') or 'Saved page',
                'kind': 'article', 'authors': [], 'source': 'discovery', 'origins': ['Your selected bookmarks'],
                'summary': '', 'abstract': '', 'topics': [], 'evidence_level': 'saved_link',
                'evidence': [{'url': url, 'note': 'Explicitly imported selected bookmark; saving does not establish reading or endorsement.'}],
                'duration_seconds': None, 'limitations': ['Bookmark link has not been independently revalidated in this queue.']})
    probe_key = store.get_checkpoint('active_candidate_batch')
    probe = store.get_checkpoint(probe_key, {}) if probe_key else {}
    if probe:
        try:
            snapshot = _load_json(probe['source_snapshot'])
            excerpts = {r['repo']: r['result']['structuredContent']['content']
                for r in snapshot['connector_cache']['responses']
                if r['kind'] == 'readme' and not r['result'].get('isError')}
        except (OSError, ValueError, KeyError, TypeError):
            excerpts = {}
        for candidate in probe.get('candidates', []):
            works.append({'url': candidate['repository_url'], 'title': candidate['repository_full_name'],
                'kind': 'code', 'authors': [candidate['repository_full_name'].split('/')[0]],
                'source': 'discovery', 'source_entity_id': candidate['entity_id'],
                'origins': ['Earlier project research'], 'summary': '',
                'learn': candidate['why'], 'description': excerpts.get(candidate['repository_full_name'], '')[:4000],
                'evidence_level': 'earlier_work_notes', 'duration_seconds': None,
                'evidence': [{'url': candidate['readme_source'],
                    'note': 'Earlier cached README excerpt; SHA ' + candidate['readme_blob_sha']}],
                'limitations': candidate['limitations']})
    return works, {'status': 'ready', 'creator_cards': report['metrics']['recommendations'],
                   'works': len(works), 'source_batches': len(report['rounds'])}


def validate_research(data):
    if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('works'), list) or not 1 <= len(data['works']) <= 30:
        raise ValueError('Learning research requires version 1 and 1..30 assessed works')
    seen = set()
    for row in data['works']:
        if not isinstance(row, dict):
            raise ValueError('Assessed learning works must be objects')
        url = canonical_url(row.get('url', ''))
        if url in seen:
            raise ValueError('Duplicate learning research URL')
        seen.add(url)
        for field in ('title', 'summary', 'learn', 'start_here', 'prerequisites'):
            if field in row and (not isinstance(row[field], str) or len(row[field]) > 10000):
                raise ValueError('Learning descriptions must be bounded text')
        for field in ('authors', 'topics', 'limitations'):
            values = row.get(field, [])
            if not isinstance(values, list) or len(values) > 100 or any(not isinstance(v, str) for v in values):
                raise ValueError('Learning metadata fields must be lists of text')
        if (row.get('kind') not in KINDS or not row.get('title') or not row.get('summary') or
                not row.get('learn') or not row.get('limitations') or not row.get('evidence') or
                row.get('evidence_level') not in ('metadata_revalidated', 'documentation_excerpt', 'paper_excerpt')):
            raise ValueError('Assessed works need specific learning value, scope, evidence and limitations')
        if not isinstance(row.get('verified_at'), str):
            raise ValueError('Research needs a verification date')
        date = datetime.fromisoformat(row['verified_at'].replace('Z', '+00:00'))
        if date.tzinfo is None:
            raise ValueError('Research dates need a timezone')
        for field in ('evidence', 'bridges'):
            if not isinstance(row.get(field, []), list) or len(row.get(field, [])) > 100:
                raise ValueError('Research evidence and bridges must be bounded lists')
        for evidence in row['evidence']:
            if not isinstance(evidence, dict) or not isinstance(evidence.get('note'), str):
                raise ValueError('Evidence must contain a written inspection note')
            canonical_url(evidence.get('url', ''))
            if not evidence.get('note'):
                raise ValueError('Research evidence needs a bounded inspection note')
        if row.get('start_url'):
            canonical_url(row['start_url'])
            if canonical_url(row['start_url']) != url:
                raise ValueError('A chapter link must target the same learning work')
        for bridge in row.get('bridges', []):
            if (not isinstance(bridge, dict) or not isinstance(bridge.get('explanation'), str) or
                    not isinstance(bridge.get('terms'), list) or
                    not all(isinstance(t, str) for t in bridge['terms']) or
                    not isinstance(bridge.get('sources'), list) or
                    not bridge['terms'] or not bridge['explanation'] or not bridge['sources']):
                raise ValueError('Method bridges need query terms, an explanation and sources')
            for source in bridge['sources']:
                canonical_url(source)
        if row.get('duration_seconds') is not None and (type(row['duration_seconds']) is not int or row['duration_seconds'] <= 0):
            raise ValueError('Known durations must be positive measured seconds')


def import_research(store, source):
    data = _load_json(source)
    validate_research(data)
    digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    private_json(store.folder / 'sources' / ('learning-research-' + digest + '.json'), data)
    with store.db:
        store.checkpoint('learning_research', data)
    return refresh(store)


def refresh(store, arxiv_dir=None):
    initialize(store)
    settings = store.get_checkpoint('learning_settings', {})
    selected = arxiv_dir if arxiv_dir is not None else os.environ.get('ARXIV_SHELF_DIR') or settings.get('arxiv_dir') or str(Path.home() / 'git/arxiv-shelf')
    settings['arxiv_dir'] = str(Path(selected).expanduser().resolve())
    collection, states = [], {}
    for name, loader in [('shelf', lambda: load_shelf(selected)), ('discovery', lambda: _discovery(store))]:
        try:
            rows, state = loader()
            collection.extend(rows)
            states[name] = {**state, 'checked_at': now()}
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            states[name] = {'status': 'unavailable', 'checked_at': now(),
                'message': ('arXiv Shelf catalog could not be read; cached papers remain searchable. Check --arxiv-dir and the catalog event format.' if name == 'shelf' else
                            'Creator research is unavailable; other and cached sources remain searchable.')}
            # Retain the last successful partition, including reviews and curation.
            for record in store.db.execute('SELECT payload FROM learning_works WHERE active=1'):
                row = json.loads(record[0])
                if row.get('source') == name:
                    collection.append(row)
    merged = {}
    for row in collection:
        key = work_id(row['url'])
        if key in merged:
            prior = merged[key]
            prior['origins'] = list(dict.fromkeys(prior['origins'] + row.get('origins', [])))
            prior['creator_ids'] = list(dict.fromkeys(prior.get('creator_ids', []) + row.get('creator_ids', [])))
            if row.get('source_entity_id'):
                prior['source_entity_id'] = row['source_entity_id']
            if row.get('description') and not prior.get('description'):
                prior['description'] = row['description']
        else:
            merged[key] = dict(row, id=key)
    research = store.get_checkpoint('learning_research', {'works': []})
    for extra in research['works']:
        key = work_id(extra['url'])
        old = merged.get(key, {})
        merged[key] = {**old, **extra, 'id': key, 'url': canonical_url(extra['url']),
            'source': old.get('source', 'research'),
            'origins': list(dict.fromkeys(old.get('origins', []) + ['Newly researched']))}
    changed = 0
    with store.db:
        store.db.execute('UPDATE learning_works SET active=0')
        for key, row in merged.items():
            row.setdefault('origins', [])
            encoded = json.dumps(row, sort_keys=True, ensure_ascii=False)
            digest = hashlib.sha256(encoded.encode()).hexdigest()
            existing = store.db.execute('SELECT digest FROM learning_works WHERE id=?', (key,)).fetchone()
            if existing and existing[0] == digest:
                store.db.execute('UPDATE learning_works SET active=1 WHERE id=?', (key,))
                continue
            ev = store.evidence('learning_work', row['url'], completeness='partial',
                notes={'origins': row['origins'], 'scope': row.get('evidence_level'), 'digest': digest})
            store.entity(key, 'learning_work', key, row['title'], ev, url=row['url'])
            store.db.execute('INSERT INTO learning_works VALUES (?,?,?,?,1) ON CONFLICT(id) DO UPDATE SET '
                'payload=excluded.payload,digest=excluded.digest,updated_at=excluded.updated_at,active=1',
                (key, encoded, digest, now()))
            changed += 1
        states['index'] = {'active_works': len(merged), 'changed': changed, 'refreshed_at': now(),
                           'researched': len(research['works']), 'external_requests': 0}
        store.checkpoint('learning_settings', settings)
        store.checkpoint('learning_sources', states)
    private_json(store.folder / 'learning_coverage.json', {'visibility': 'private', **states})
    write_learning_report(store)
    return states


def works(store, active=True):
    initialize(store)
    result = []
    for row in store.db.execute('SELECT w.payload,w.active,f.saved,f.completed,f.useful,f.notes,f.updated_at '
            'FROM learning_works w LEFT JOIN learning_feedback f ON f.work_id=w.id' + (' WHERE w.active=1' if active else '')):
        item = json.loads(row['payload'])
        item['active'] = bool(row['active'])
        item['feedback'] = {'saved': bool(row['saved']), 'completed': bool(row['completed']),
                            'useful': row['useful'], 'notes': row['notes'] or '', 'updated_at': row['updated_at']}
        result.append(item)
    return result


def feedback(store, payload):
    initialize(store)
    if not isinstance(payload, dict) or payload.get('action') not in ('saved', 'completed', 'useful', 'dismissed', 'notes'):
        raise ValueError('Invalid learning feedback action')
    key, action = payload.get('id'), payload['action']
    if not isinstance(key, str) or not store.db.execute('SELECT 1 FROM learning_works WHERE id=?', (key,)).fetchone():
        raise ValueError('Unknown learning work')
    if action != 'notes' and type(payload.get('value')) is not bool:
        raise ValueError('Learning feedback needs a boolean value')
    notes = payload.get('notes')
    if notes is not None and (not isinstance(notes, str) or len(notes) > 4000):
        raise ValueError('Notes must contain at most 4000 characters')
    prior = store.db.execute('SELECT saved,completed,useful,notes FROM learning_feedback WHERE work_id=?', (key,)).fetchone()
    state = dict(prior) if prior else {'saved': False, 'completed': False, 'useful': None, 'notes': ''}
    if action in ('saved', 'completed'):
        state[action] = payload['value']
    elif action == 'useful':
        state['useful'] = 1 if payload['value'] else None
    elif action == 'dismissed':
        state['useful'] = -1 if payload['value'] else None
    if notes is not None:
        state['notes'] = notes
    if prior and state == dict(prior):
        return state
    with store.db:
        ev = store.evidence('learning_feedback', key, notes=state)
        store.db.execute('INSERT INTO learning_feedback VALUES (?,?,?,?,?,?,?) ON CONFLICT(work_id) DO UPDATE SET '
            'saved=excluded.saved,completed=excluded.completed,useful=excluded.useful,notes=excluded.notes,'
            'updated_at=excluded.updated_at,evidence_id=excluded.evidence_id',
            (key, state['saved'], state['completed'], state['useful'], state['notes'], now(), ev))
    return state


def _time_label(row, budget):
    seconds = row.get('duration_seconds')
    if not seconds:
        return 'Duration unknown', 0
    minutes = math.ceil(seconds / 60)
    ceiling = {'short': 15, 'medium': 45, 'substantial': 120}.get(budget)
    return (f'{seconds // 60} min {seconds % 60:02d} sec video' + (' · longer than this session' if ceiling and minutes > ceiling else ''),
            1 if ceiling and minutes <= ceiling else -1 if ceiling else 0)


def search(store, query='', *, goal='', time='', format='', view='', limit=None):
    if not isinstance(query, str) or len(query) > 500 or goal not in GOALS or time not in TIMES or format not in FORMATS or view not in ('', 'saved', 'completed', 'useful', 'dismissed'):
        raise ValueError('Invalid learning search options')
    allworks = works(store, active=not bool(view))
    q = tokens(query)
    if not q and not view:
        return {'visibility': 'private', 'results': [], 'related': None, 'message': 'Enter a subject or question to choose a learning session.',
                'sources': store.get_checkpoint('learning_sources', {})}
    documents = [tokens(' '.join((r['title'], r.get('summary', ''), r.get('abstract', ''),
                                 r.get('description', ''), ' '.join(r.get('topics', []))))) for r in allworks]
    df = Counter(t for doc in documents for t in doc)
    # Require a specific query anchor, not just a generic shared word such as
    # "search". A source-linked method bridge can explain an adjacent match.
    bridge_vocabulary = {t for row in allworks for b in row.get('bridges', [])
                         for t in tokens(' '.join(b['terms']))}
    known = {t for t in q if df[t] or t in bridge_vocabulary}
    # Unrecognized conversational words must not veto a supported subject.
    # Unknown-only queries still have no anchor and return an honest empty state.
    anchors = {t for t in known if df[t] == min((df[x] for x in known), default=0)}
    ranked = []
    existing_reviews = {r['entity_id']: r['decision'] for r in store.db.execute('SELECT entity_id,decision FROM reviews')}
    for row, doc in zip(allworks, documents):
        f = row['feedback']
        if view and not (f['useful'] == (-1 if view == 'dismissed' else 1) if view in ('dismissed', 'useful') else f[view]):
            continue
        if not view and (f['useful'] == -1 or f['completed']):
            continue
        if not view and existing_reviews.get(row.get('source_entity_id')) in ('skip', 'not_interesting') and f['useful'] != 1:
            continue
        if format and row['kind'] not in {'watch': ('video',), 'read': ('paper', 'article'), 'code': ('code', 'demo')}[format]:
            continue
        title = tokens(row['title'])
        hits = q & doc
        bridges = [b for b in row.get('bridges', []) if anchors & tokens(' '.join(b['terms']))]
        direct = bool(hits) and bool(hits & anchors) and len(hits) >= min(2, len(q))
        if q and not bridges and not direct:
            continue
        # IDF and exact work text dominate. Creator-wide interests aren't copied
        # into work text: a parent mentioning Reversi does not make its art relevant.
        lexical = sum((4 if t in title else 1.8) * (1 + math.log(1 + len(allworks) / (1 + df[t]))) for t in hits)
        method = bridges[0] if bridges else None
        evidence = row.get('evidence_level', 'catalog_metadata')
        strong = evidence in ('documentation_excerpt', 'paper_excerpt')
        effort, fit = _time_label(row, time)
        bonus = (3 if strong else 1 if evidence == 'metadata_revalidated' else 0) + fit
        if goal == 'overview' and row['kind'] in ('video', 'article'):
            bonus += 1
        if goal == 'deep' and strong:
            bonus += 1
        if goal == 'revisit' and (f['saved'] or 'Your arXiv Shelf' in row['origins']):
            bonus += 2
        if goal == 'adjacent' and method:
            bonus += 2
        # Parent reviews affect only weak triage; familiarity never means completion.
        parent_decisions = [existing_reviews.get(key) for key in row.get('creator_ids', [])]
        if any(d in ('skip', 'not_interesting') for d in parent_decisions):
            bonus -= 4
        if 'already_familiar' in parent_decisions:
            bonus -= .5
        if f['useful'] == 1:
            bonus += .5
        elif f['saved']:
            bonus -= .25  # saved material stays available in its own view
        strength = {'saved_link': .3, 'catalog_metadata': .55, 'earlier_work_notes': .7,
                    'metadata_revalidated': .9}.get(evidence, 1)
        score = lexical * strength + bonus + (3 if method else 0)
        relation = 'Method connection' if method and (not direct or method.get('prefer')) else 'Direct topic match'
        # Explicit bridge terms are not inserted as fake title/abstract matches.
        reason = (method['explanation'] if method and (not direct or method.get('prefer')) else
                  'Matches ' + ', '.join(sorted(hits)[:4]) + ' in this work’s ' + ('title' if hits & title else 'description or abstract') + '.')
        if view and not q:
            relation, reason = 'Your collection', 'Shown from your ' + view + ' works; feedback on each dimension remains separate.'
        abstract = row.get('abstract', '')
        preview = abstract[:350].rsplit(' ', 1)[0] + '…' if len(abstract) > 350 else abstract
        copy = {**row, 'relation': relation, 'reason': reason, 'effort': effort,
            'learn': row.get('learn') or row.get('summary') or
                     ('Abstract excerpt: ' + preview if preview else 'Open the source to assess whether it addresses your question.'),
            'facets': {'topical_fit': 'Work text: ' + ', '.join(sorted(hits)) if hits else 'No exact work-text hit',
                'methodological_fit': method['explanation'] if method else 'No separate method claim',
                'explanatory_usefulness': row.get('start_here', 'Full explanatory quality not assessed'),
                'novelty': 'Your prior familiarity with this work is unknown' if not f['completed'] else 'Marked already read/watched by you',
                'evidence_strength': evidence.replace('_', ' '), 'session_effort': effort}}
        ranked.append((score, copy))
    ranked.sort(key=lambda x: (-x[0], x[1]['title']))
    chosen, creators, families, kinds = [], Counter(), set(), Counter()
    pool = ranked[:]
    requested = limit if limit is not None else 30 if view else 5
    while pool and len(chosen) < min(max(requested, 1), 5 if not view else 30):
        best = max(range(len(pool)), key=lambda i: pool[i][0] -
            sum(creators[c] * 3 for c in pool[i][1].get('creator_ids', [])) - kinds[pool[i][1]['kind']] * .6)
        _, row = pool.pop(best)
        family = row.get('arxiv_base', row['id'])
        if family in families:
            continue
        families.add(family)
        chosen.append(row)
        creators.update(row.get('creator_ids', [])); kinds[row['kind']] += 1
    related = next(({'label': b.get('label', 'Related concept'), 'explanation': b['explanation'],
                     'sources': b['sources']} for row in chosen for b in row.get('bridges', [])), None)
    return {'visibility': 'private', 'results': chosen, 'related': related, 'matched': len(ranked),
        'message': ('No supported matches in the current local collection. Try a broader subject or a different format.' if not chosen else
                    'A small shortlist from your local collections. Opening a link does not mark it completed.'),
        'sources': store.get_checkpoint('learning_sources', {})}


def write_learning_report(store):
    """Private handoff, including actual inspected works and reproducible queries."""
    research = store.get_checkpoint('learning_research', {'works': []})
    rows = research['works']
    lines = ['# Private Learning Queue research', '', 'Generated ' + now(), '',
        '## Coverage', '', '```json', json.dumps(store.get_checkpoint('learning_sources', {}), indent=2), '```', '',
        '## Additional research accounting', '', '```json', json.dumps(research.get('accounting', {}), indent=2), '```', '',
        'Source metadata and bounded written/code excerpts were inspected. No candidate code ran and no full video was watched.',
        'Titles, identifiers and source links were revalidated; this does not establish full technical correctness, video availability in every region, or personal usefulness.',
        'Individual reading times remain unknown. Known video durations come from fresh official API metadata.', '',
        '## Example query audit', '', 'These are system-level topical checks, not human relevance ratings. Format and session choices can change the order.']
    evaluations = {}
    for query in research.get('demonstration_queries', []):
        result = search(store, query)
        evaluations[query] = result
        lines += ['', '### ' + query, '']
        lines += ['- [' + r['title'] + '](' + r['url'] + ') · ' + r['kind'] + ' · ' + r['relation'] + ': ' + r['reason']
                  for r in result['results']] or ['No supported matches in the indexed collection.']
    lines += ['', '## Independently researched works', '']
    for row in rows:
        lines += ['### ' + row['title'], '', '[' + row['kind'] + '](' + row['url'] + ') · checked ' + row['verified_at'], '',
            row['summary'], '', 'Learn: ' + row['learn'], '', 'Start: ' + row.get('start_here', 'Not established'), '',
            'Suggested background: ' + row.get('prerequisites', 'Unknown'), '',
            'Evidence: ' + row['evidence_level'].replace('_', ' '), '']
        lines += ['- [' + e['url'] + '](' + e['url'] + '): ' + e['note'] for e in row['evidence']]
        lines += ['', 'Limitations:'] + ['- ' + x for x in row['limitations']] + ['']
    lines += ['## Limitations and useful next work', '',
        '- The ' + str(len(rows)) + '-work research pilot is intentionally bounded; the larger corpus includes older work notes, abstracts and unvalidated saved links.',
        '- Shelf ratings are read-only source metadata. No rating, reading event or long-term preference was inferred.',
        '- Vortex suggestions teach methods and numerical cautions; they are not a validated reference solution for the current solver.',
        '- Spectral audio processing is adjacent to transcription; only the explicit transcription resource is presented as an AMT implementation.',
        '- The current index uses transparent lexical matching and documented bridges. It may miss paraphrases or underdeveloped topics.',
        '- A first-pass keyword baseline returned scientific-search papers for a game-search question. Specific query anchors remove this observed failure; this is not a claim of improved human usefulness.',
        '- Next, inspect one full selected lesson, test a small example, and add work-specific feedback. Focus further research on unsupported queries rather than expanding indiscriminately.',
        '- Source refresh is local and offline. Newly verified external research enters through an explicit private manifest import.', '']
    private_write(store.folder / 'learning_research_report.md', '\n'.join(lines).encode())
    private_json(store.folder / 'learning_query_examples.json', {'visibility': 'private', 'queries': evaluations})
