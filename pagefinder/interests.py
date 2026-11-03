"""Curated bookshelf evidence and bounded, reviewable concept hypotheses.

This records a title-level map, not full-text analysis or calibrated preferences.
The public keyword baseline remains an independent, unchanged comparator.
"""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from .core import ROOT, score as keyword_score
from .privacy import private_json, private_write
from .research import stable_id

DEFAULT_SOURCE = ROOT / 'BOOKSHELF_INTEREST_EVIDENCE.md'
DEFAULT_SEEDS = ROOT / 'data/bookshelf_seeds.json'
DEFAULT_BASELINE = ROOT / 'data/interests.json'
POLICY = [
    'Physical visibility supports access/curiosity, not reading, proficiency or endorsement.',
    'All book importance and per-book reading statuses remain unspecified until reviewed.',
    'One bookshelf photograph is one evidence family; repeated introductory topics do not multiply preference strength.',
    'Book subjects, existing keyword hypotheses, private engagement and adjacent research proposals remain distinct.',
    'Relationship confidence describes the mapping, not personal enthusiasm; no preference weights are assigned.',
    'Only bibliographic/title-level source text was imported; no book full text or photograph was ingested.',
    'Baseline matches refer to the existing keyword profile, not a new inspection of active project repositories.',
]


def _read(path):
    with Path(path).open('rb') as handle:
        raw = handle.read(1_000_001)
    if len(raw) > 1_000_000:
        raise ValueError('Bookshelf input exceeds the 1 MB safety bound')
    return raw


def parse_books(text):
    books = {}
    for line in text.splitlines():
        if not re.match(r'^\|\s*\d+\s*\|', line):
            continue
        cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
        if len(cells) != 5:
            raise ValueError('Bookshelf table needs number, title, author, notes and concept seeds')
        number = int(cells[0])
        if number in books:
            raise ValueError('Duplicate volume number in bookshelf evidence')
        books[number] = {'number': number, 'title': cells[1].strip('*'), 'authors_as_reported': cells[2],
                         'bibliographic_notes': cells[3], 'source_concept_seeds': cells[4]}
    if not books or len(books) > 50:
        raise ValueError('Bookshelf source must contain 1..50 identified volumes')
    return books


def _validate(books, spec, baseline):
    try:
        if (spec['version'] != 1 or spec['source'] != 'bookshelf_photo_2026_11_02' or
                spec['evidence_type'] != 'physical_book_visible'):
            raise ValueError('Unsupported bookshelf seed provenance/version')
        concepts = {c['id']: c for c in spec['concepts']}
        if not 1 <= len(concepts) <= 60 or len(concepts) != len(spec['concepts']):
            raise ValueError('Duplicate or excessive concept seeds')
        if any(c['kind'] not in ('subject', 'method', 'history') for c in concepts.values()):
            raise ValueError('Book concepts require explicit subject/method/history types')
        if any(not isinstance(c['label'], str) or not re.fullmatch(r'[a-z_]+', c['id'])
               for c in concepts.values()):
            raise ValueError('Invalid concept ID or label')
        mapped = {b['number']: b for b in spec['books']}
        if set(mapped) != set(books) or len(mapped) != len(spec['books']):
            raise ValueError('Bookshelf seed coverage differs from the source table')
        norm = lambda text: ' '.join(text.casefold().split())
        for number, book in mapped.items():
            if (norm(book['title']) != norm(books[number]['title']) or not book['concepts'] or
                    any(cid not in concepts for cid in book['concepts'])):
                raise ValueError('Book identification/topic map needs review before import')
        if len(spec['hypotheses']) > 10 or len({h['id'] for h in spec['hypotheses']}) != len(spec['hypotheses']):
            raise ValueError('Hypothesis expansion exceeds the bounded seed set')
        for hypothesis in spec['hypotheses']:
            ref = urlsplit(hypothesis['reference']['url'])
            if (not hypothesis['books'] or any(n not in books for n in hypothesis['books']) or
                    any(cid not in concepts for cid in hypothesis['concepts']) or
                    not hypothesis['falsification'] or not hypothesis['entry_point'] or
                    ref.scheme != 'https' or not ref.hostname or ref.username or ref.password):
                raise ValueError('Hypothesis needs valid provenance, links and a falsification condition')
        for cluster in spec['clusters']:
            if (not isinstance(cluster['label'], str) or not isinstance(cluster['interpretation'], str) or
                    any(number not in books for number in cluster['books'])):
                raise ValueError('Malformed bookshelf cluster')
        if (not isinstance(baseline['interests'], list) or
                any(not isinstance(item, dict) or not isinstance(item.get('name'), str)
                    for item in baseline['interests'])):
            raise ValueError('Expected the existing keyword baseline')
    except (KeyError, TypeError, AttributeError):
        raise ValueError('Malformed bookshelf seed specification') from None


def import_bookshelf(store, source=DEFAULT_SOURCE, seeds=DEFAULT_SEEDS, baseline=DEFAULT_BASELINE,
                     *, overall_reading_completion=None):
    if overall_reading_completion not in (None, 'unknown', 'low', 'partial', 'high'):
        raise ValueError('Unsupported aggregate reading-completion annotation')
    raw_source, raw_seeds, raw_baseline = _read(source), _read(seeds), _read(baseline)
    books = parse_books(raw_source.decode('utf-8'))
    spec, profile = json.loads(raw_seeds), json.loads(raw_baseline)
    _validate(books, spec, profile)
    digest = hashlib.sha256(raw_source + b'\0' + raw_seeds + b'\0' + raw_baseline).hexdigest()
    key = 'bookshelf_model:' + digest
    model = store.get_checkpoint(key)
    if model is None:
        # Cache exact textual inputs, never the original photo or private reading notes.
        snapshot = store.folder / 'sources' / ('bookshelf-' + digest + '.json')
        private_json(snapshot, {'version': 1, 'visibility': 'private', 'source_markdown': raw_source.decode('utf-8'),
                                'curated_seeds': spec, 'keyword_baseline': profile})
        nodes, edge_ids = set(), set()
        book_id = lambda number: 'bookshelf:' + spec['source'] + ':' + str(number)
        concept_id = lambda cid: 'concept:bookshelf:' + cid
        with store.db:
            visible = store.evidence(spec['source'], str(snapshot), completeness='complete_for_request',
                                     observed_at='2026-11-02', notes={
                                         'source': spec['source'], 'evidence_type': spec['evidence_type'],
                                         'origin_url': spec['source_url'], 'snapshot_sha256': digest,
                                         'date_precision': 'day', 'scope': 'bibliographic transcription only',
                                         'policy': POLICY})
            mapping = store.evidence('bookshelf_title_map', str(snapshot), completeness='partial',
                                     notes={'source': spec['source'], 'role': 'curated title-level interpretation'})
            baseline_ev = store.evidence('public_keyword_baseline', str(snapshot), completeness='complete_for_request',
                                         notes={'role': 'existing hypotheses, not reviewed project evidence'})
            shelf_id = 'source:' + spec['source']
            store.entity(shelf_id, 'source_document', spec['source'], 'User-supplied bookshelf transcription',
                         visible, url=spec['source_url'])
            nodes.add(shelf_id)
            def link(subject, predicate, target, status, evidence, condition, confidence=.75):
                edge_ids.add(store.relationship(subject, predicate, target, status, evidence,
                                                confidence=confidence, falsification=condition))
            for concept in spec['concepts']:
                cid = concept_id(concept['id'])
                store.concept(cid, concept['label'], concept['kind'], mapping)
                nodes.add(cid)
            for mapped in spec['books']:
                book = books[mapped['number']]
                bid = book_id(book['number'])
                store.entity(bid, 'book', bid, book['title'], visible, url=spec['source_url'])
                nodes.add(bid)
                link(bid, 'reported_visible_in', shelf_id, 'known', visible,
                     'Correct if the user revises the identification or physical-presence report.', 1.0)
                for cid in mapped['concepts']:
                    kind = next(c['kind'] for c in spec['concepts'] if c['id'] == cid)
                    predicate = {'subject': 'covers_subject', 'method': 'uses_method',
                                 'history': 'has_historical_context'}[kind]
                    link(bid, predicate, concept_id(cid), 'inferred', mapping,
                         'Correct the title-level subject mapping or supply bibliographic clarification; this does not establish reading or preference.')
            baseline_names = {item['name'] for item in profile['interests']}
            hypotheses = []
            for seed in spec['hypotheses']:
                qid = 'question:bookshelf:' + seed['id']
                store.concept(qid, seed['question'], 'question', mapping)
                nodes.add(qid)
                for number in seed['books']:
                    link(book_id(number), 'suggests_question', qid, 'hypothesis', mapping, seed['falsification'])
                for cid in seed['concepts']:
                    link(qid, 'connects_to', concept_id(cid), 'hypothesis', mapping, seed['falsification'])
                for topic in seed['baseline_topics']:
                    if topic in baseline_names:
                        aid = 'concept:baseline:' + stable_id(topic)
                        store.concept(aid, topic, 'baseline', baseline_ev)
                        nodes.add(aid)
                        link(qid, 'adjacent_to_keyword_hypothesis', aid, 'hypothesis', baseline_ev,
                             'Confirm against actual project documentation and user feedback; the keyword baseline alone is not proof of priority.')
                ref = seed['reference']
                ref_ev = store.evidence('public_research_reference', ref['url'], visibility='public',
                                       retrieved_at=ref['checked'], completeness='partial', notes={
                                           'scope': ref['scope'], 'cached': 'citation metadata and scoped summary only'})
                rid = 'reference:' + stable_id(ref['url'])
                store.entity(rid, 'public_reference', ref['url'], ref['title'], ref_ev, url=ref['url'])
                nodes.add(rid)
                link(qid, 'has_research_reference', rid, 'known', ref_ev,
                     'Recheck the linked primary source; its existence does not confirm user interest.', 1.0)
                hypotheses.append({**seed, 'entity_id': qid, 'book_ids': [book_id(n) for n in seed['books']]})
            model = {'version': 1, 'visibility': 'private', 'source': spec['source'],
                     'evidence_type': spec['evidence_type'], 'snapshot_sha256': digest, 'source_snapshot': str(snapshot),
                     'policy': POLICY, 'node_ids': sorted(nodes), 'edge_ids': sorted(edge_ids),
                     'books': [{**book, 'entity_id': book_id(number), 'reading_status': 'unspecified',
                                'discovery_priority': 'unspecified'} for number, book in sorted(books.items())],
                     'clusters': spec['clusters'], 'hypotheses': hypotheses,
                     'independent_photograph_sources': 1, 'preference_weights_assigned': False,
                     'expansion_depth': 1, 'hypothesis_limit': 10, 'external_requests_by_importer': 0}
            store.checkpoint(key, model)
    with store.db:
        store.checkpoint('active_bookshelf_model', key)
        if overall_reading_completion is not None:
            existing = store.get_checkpoint('bookshelf_reading_feedback', {})
            if existing.get('overall') != overall_reading_completion:
                ev = store.evidence('manual_bookshelf_feedback', spec['source'], notes={
                    'overall_reading_completion': overall_reading_completion, 'scope': 'aggregate_only',
                    'per_book_completion': 'unspecified', 'interest_strength_change': 'none'})
                store.checkpoint('bookshelf_reading_feedback', {'overall': overall_reading_completion,
                    'scope': 'aggregate_only', 'per_book': 'unspecified', 'evidence_id': ev})
    return write_interest_graph(store)


def set_interest_scope(store, topic, label, contexts, *, project_status='unspecified', note='', mode='require'):
    """A durable private correction overrides weak source-derived topic hypotheses."""
    baseline = json.loads(_read(DEFAULT_BASELINE))
    if topic not in {t['name'] for t in baseline['interests']}:
        raise ValueError('Choose an existing baseline topic for this scope correction')
    contexts = list(dict.fromkeys(c.strip().casefold() for c in contexts if isinstance(c, str) and c.strip()))
    if not label.strip() or not 1 <= len(contexts) <= 40 or any(len(c) > 80 for c in contexts):
        raise ValueError('Scope corrections need a label and 1..40 short context terms')
    if project_status not in ('unspecified', 'active', 'stopped'):
        raise ValueError('Unsupported user-reported project status')
    if mode not in ('require', 'prefer'):
        raise ValueError('Scope mode must require or prefer the named application context')
    payload = {'topic': topic, 'preferred_label': label, 'required_context_terms': contexts,
               'related_project_status': project_status, 'note': note,
               'mode': mode, 'off_context_allowance': 'small_exploratory' if mode == 'prefer' else 'none',
               'policy': ('Prefer the named application context; allow a small number of general exploratory suggestions.'
                          if mode == 'prefer' else 'Require application context before using this topic as a retrieval reason.'),
               'priority': 'overrides_source_inference', 'semantic_context_review_required': True}
    digest = stable_id(payload)
    snapshot = store.folder / 'sources' / ('interest-scope-' + digest + '.json')
    private_json(snapshot, {'visibility': 'private', **payload})
    key = 'interest_scope:' + stable_id(topic)
    previous = store.get_checkpoint(key)
    if previous is None or previous['payload_digest'] != digest:
        with store.db:
            ev = store.evidence('manual_interest_scope', str(snapshot), notes=payload)
            baseline_id = 'concept:baseline:' + stable_id(topic)
            scope_id = 'scope:' + stable_id(topic, label)
            store.concept(baseline_id, topic, 'baseline', ev)
            store.concept(scope_id, label, 'subject', ev)
            rid = store.relationship(baseline_id, 'prefers_context' if mode == 'prefer' else 'requires_context', scope_id, 'known', ev,
                                     confidence=1.0, falsification='Change only when the user revises this explicit scope.')
            store.checkpoint(key, {**payload, 'payload_digest': digest, 'evidence_id': ev,
                                    'node_ids': [baseline_id, scope_id], 'edge_id': rid})
    if store.get_checkpoint('active_bookshelf_model'):
        return write_interest_graph(store)
    return store.get_checkpoint(key)


def score_private(row, profile):
    """Keep the public comparator untouched; gate private topic contributions."""
    fields = [row.get(k) or '' for k in ('title', 'summary', 'repo_description', 'body', 'topics')]
    text = ' '.join(' '.join(map(str, v)) if isinstance(v, list) else str(v) for v in fields)
    allowed, suppressed, exploratory = [], [], []
    for topic in profile['interests']:
        terms = topic.get('required_context_terms', [])
        if terms and not any(re.search(r'(?<!\w)' + re.escape(t) + r'(?!\w)', text, re.I) for t in terms):
            if topic.get('context_policy') == 'prefer':
                allowed.append(topic)
                exploratory.append(topic['name'])
            else:
                suppressed.append(topic.get('baseline_topic', topic['name']))
        else:
            allowed.append(topic)
    result = keyword_score(row, allowed)
    exploratory_matches = [f for f in result['evidence'] if f['topic'] in exploratory]
    return {**result, 'visibility': 'private', 'context_suppressed_topics': suppressed,
            'exploratory_topics': [f['topic'] for f in exploratory_matches],
            'primary_points': sum(f['points'] for f in result['evidence'] if f['topic'] not in exploratory),
            'exploratory_points': sum(f['points'] for f in exploratory_matches),
            'selection_policy': 'Prefer primary matches; allow a small exploratory supplement. Batch quotas are not yet implemented.',
            'limitation': 'Context keywords are triage; semantic application relevance still needs review.'}


def write_interest_graph(store):
    key = store.get_checkpoint('active_bookshelf_model')
    if not key:
        raise ValueError('Import bookshelf evidence before generating its graph report')
    report = store.get_checkpoint(key)
    def review(entity_id):
        row = store.db.execute('SELECT decision,reason,updated_at FROM reviews WHERE entity_id=?', (entity_id,)).fetchone()
        return dict(row) if row else {'decision': 'unknown', 'reason': ''}
    nodes = []
    for nid in report.pop('node_ids'):
        row = store.db.execute('SELECT id,kind,title,canonical_url,evidence_id FROM entities WHERE id=?', (nid,)).fetchone()
        nodes.append({**dict(row), 'review': review(nid)})
    report['relationships'] = [dict(store.db.execute('SELECT * FROM relationships WHERE id=?', (rid,)).fetchone())
                               for rid in report.pop('edge_ids')]
    scopes = [json.loads(row[0]) for row in store.db.execute(
        "SELECT value FROM checkpoints WHERE key LIKE 'interest_scope:%' ORDER BY key")]
    report['interest_scope_corrections'] = scopes
    seen_nodes = {n['id'] for n in nodes}
    for scope in scopes:
        for nid in scope['node_ids']:
            if nid not in seen_nodes:
                row = store.db.execute('SELECT id,kind,title,canonical_url,evidence_id FROM entities WHERE id=?', (nid,)).fetchone()
                nodes.append({**dict(row), 'review': review(nid)})
                seen_nodes.add(nid)
        report['relationships'].append(dict(store.db.execute('SELECT * FROM relationships WHERE id=?', (scope['edge_id'],)).fetchone()))
    report['nodes'] = nodes
    snapshot = json.loads(Path(report['source_snapshot']).read_text(encoding='utf-8'))
    effective = snapshot['keyword_baseline']
    corrections = {s['topic']: s for s in scopes}
    for topic in effective['interests']:
        if topic['name'] in corrections:
            correction = corrections[topic['name']]
            topic['baseline_topic'] = topic['name']
            topic['name'] = correction['preferred_label']
            topic['required_context_terms'] = correction['required_context_terms']
            topic['context_policy'] = correction.get('mode', 'require')
            topic['scope_evidence_id'] = correction['evidence_id']
    report['effective_keyword_profile'] = {'visibility': 'private', **effective,
        'weight_status': 'Existing comparator weights are uncalibrated; explicit context restrictions take precedence.'}
    for book in report['books']:
        book['review'] = review(book['entity_id'])
    for hypothesis in report['hypotheses']:
        hypothesis['review'] = review(hypothesis['entity_id'])
        hypothesis['eligible_for_exploration'] = (hypothesis['review']['decision'] != 'skip' and
                                                any(review(bid)['decision'] != 'skip' for bid in hypothesis['book_ids']))
        hypothesis['context_requirements'] = [corrections[t] for t in hypothesis['baseline_topics'] if t in corrections]
        if hypothesis['context_requirements']:
            if any(s.get('mode', 'require') == 'require' for s in hypothesis['context_requirements']):
                hypothesis['eligible_for_exploration'] = False
                hypothesis['scope_status'] = 'requires_application_connection_before_exploration'
            else:
                hypothesis['scope_status'] = 'exploratory_until_preferred_application_is_established'
        else:
            hypothesis['scope_status'] = 'unreviewed_proposal'
    report['reading_completion_feedback'] = store.get_checkpoint('bookshelf_reading_feedback', {
        'overall': 'unspecified', 'scope': 'aggregate_only', 'per_book': 'unspecified'})
    report['entry_point_policy'] = 'Offer optional prerequisites and small examples alongside deep material; do not infer proficiency or impose a beginner-only ranking.'
    report['source_coverage'] = store.coverage()
    private_json(store.folder / 'interest_graph.json', report)
    private_json(store.folder / 'interest_profile.json', report['effective_keyword_profile'])
    _write_viewer(store.folder / 'interest_graph.html', report)
    private_json(store.folder / 'evidence_coverage.json', store.coverage())
    return report


def _write_viewer(path, report):
    h = lambda value: html.escape(str(value or ''), quote=True)
    books = ''.join('<tr><td>' + str(b['number']) + '</td><td>' + h(b['title']) + '<br><small>' +
                    h(b['authors_as_reported']) + '</small></td><td>' + h(b['source_concept_seeds']) +
                    '</td><td>' + h(b['review']['decision']) + '</td></tr>' for b in report['books'])
    cards = []
    for q in report['hypotheses']:
        ref = q['reference']
        cards.append('<article><h3>' + h(q['question']) + '</h3><p><strong>Hypothesis:</strong> ' +
                     h(q['connection']) + '</p><p><strong>Entry point:</strong> ' + h(q['entry_point']) +
                     '</p><p><strong>What could change this:</strong> ' + h(q['falsification']) +
                     '</p><p>Books: ' + h(', '.join(map(str, q['books']))) + ' · Review: ' +
                     h(q['review']['decision']) + ' · Eligible: ' + h(str(q['eligible_for_exploration'])) +
                     ' · Scope: ' + h(q['scope_status']) +
                     '</p><p><a target="_blank" rel="noopener noreferrer" href="' + h(ref['url']) + '">' +
                     h(ref['title']) + '</a></p><small>' + h(ref['scope']) + '</small></article>')
    clusters = ''.join('<li><strong>' + h(c['label']) + '</strong>: ' + h(c['interpretation']) + '</li>'
                       for c in report['clusters'])
    scopes = ''.join('<li><strong>' + h(s['preferred_label']) + '</strong>: ' + h(s['note']) +
                     ' · Related projects: ' + h(s['related_project_status']) +
                     ' · Policy: ' + h(s['policy']) + '</li>'
                     for s in report['interest_scope_corrections'])
    page = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'none'; base-uri 'none'; form-action 'none'">
<title>Private bookshelf interest graph</title><style>
body{font:16px system-ui;background:#fafbfc;color:#172b40;margin:2rem;line-height:1.5}main{max-width:1100px;margin:auto}
article,table{background:white;border:1px solid #dde3e9;border-radius:.5rem}article{padding:1rem;margin:1rem 0}table{width:100%;border-collapse:collapse}
td,th{padding:.7rem;text-align:left;border-bottom:1px solid #dde3e9;vertical-align:top}input{font:inherit;padding:.5rem}
</style><main><h1>Bookshelf evidence and research connections</h1><p>Title-level curiosity evidence. Reading, proficiency and current priority are not implied.
Repeated introductory topics do not create preference weights. Baseline links are keyword hypotheses, not a completed project study.</p>
<p>Overall reading completion (user report): ''' + h(report['reading_completion_feedback']['overall']) + '''.
Per-book completion remains unspecified. Entry points are optional; deeper material remains eligible.</p>
<h2>Explicit interest corrections</h2><ul>''' + scopes + '''</ul>
<label>Filter books and questions <input id="filter" type="search"></label><h2>Candidate themes</h2><ul>''' + clusters + '''</ul>
<h2>Books</h2><table><thead><tr><th>#</th><th>Book / reported authors</th><th>Source concept seeds</th><th>Review</th></tr></thead><tbody>''' + books + '''</tbody></table>
<h2>Exploratory questions</h2>''' + ''.join(cards) + '''
<h2>For your review</h2><ol><li>Which three books or themes matter most now?</li><li>Which are mainly reference material or low priority?</li>
<li>Which proposed connections are useful, uninteresting or missing the point?</li></ol>
<p>Reply in chat, or use the local review command with a book/question ID from interest_graph.json. Explicit skips suppress future exploration eligibility; reviews survive imports.
No book full text or original photograph was imported. No public catalog scores were changed.</p></main>
<script>document.querySelector('#filter').addEventListener('input',e=>{const v=e.target.value.toLowerCase();for(const n of document.querySelectorAll('tbody tr,article'))n.hidden=!n.textContent.toLowerCase().includes(v)});</script></html>'''
    private_write(path, page.encode())
