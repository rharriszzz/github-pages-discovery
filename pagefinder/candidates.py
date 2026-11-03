"""A small private review queue from cached, manually assessed public repo probes."""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path

from .core import ROOT, score
from .interests import score_private
from .privacy import outside_repo, private_json, private_write
from .research import stable_id


def _read(path):
    path = outside_repo(path)
    if path.stat().st_size > 20_000_000:
        raise ValueError('Candidate input exceeds the 20 MB safety bound')
    return path.read_bytes()


def import_candidate_batch(store, source):
    source = outside_repo(source)
    raw = _read(source)
    batch = json.loads(raw)
    if batch.get('version') != 1 or not isinstance(batch.get('candidates'), list) or not 1 <= len(batch['candidates']) <= 20:
        raise ValueError('Candidate batches require version 1 and 1..20 assessed repositories')
    artifacts = {}
    for name in ('connector_cache', 'site_checks'):
        path = (source.parent / batch[name]).resolve()
        if not path.is_relative_to(source.parent):
            raise ValueError('Candidate cache references must stay beside the selected batch')
        artifacts[name] = _read(path)
    connector = json.loads(artifacts['connector_cache'])
    site_checks = json.loads(artifacts['site_checks'])
    metadata, readmes = {}, {}
    for response in connector['responses']:
        result = response['result']
        if result.get('isError'):
            continue
        if response['kind'] == 'metadata':
            metadata[response['repo']] = json.loads(result['structuredContent']['content'])
        elif response['kind'] == 'readme':
            readmes[response['repo']] = result['structuredContent']
    sites = {row['url']: row for row in site_checks['results']}
    seen = set()
    for candidate in batch['candidates']:
        name = candidate['repository_full_name']
        if name in seen or name not in metadata or name not in readmes:
            raise ValueError('Each candidate needs unique repository metadata and a successful cached README')
        seen.add(name)
        meta = metadata[name]
        if (meta.get('private') is not False or meta.get('full_name') != name or
                meta['owner']['type'] not in ('User', 'Organization') or
                not isinstance(meta.get('id'), int) or meta.get('html_url') != 'https://github.com/' + name):
            raise ValueError('Candidate metadata does not establish the expected public repository')
        if not candidate.get('why') or not isinstance(candidate.get('facets'), dict) or not candidate.get('limitations'):
            raise ValueError('Candidates need separate reasons, facets and limitations')
    digest = hashlib.sha256(raw + artifacts['connector_cache'] + artifacts['site_checks']).hexdigest()
    snapshot = store.folder / 'sources' / ('candidate-batch-' + digest + '.json')
    private_json(snapshot, {'visibility': 'private', 'batch': batch, 'connector_cache': connector,
                            'site_checks': site_checks})
    prior = store.get_checkpoint('candidate_batch:' + digest)
    if prior is None:
        baseline = json.loads((ROOT / 'data/interests.json').read_text())
        private_profile = json.loads((store.folder / 'interest_profile.json').read_text())
        records = []
        with store.db:
            ev = store.evidence('bounded_public_repository_review', str(snapshot), completeness='partial',
                                 notes={'scope': 'metadata and bounded README excerpts; two selected HTML checks',
                                        'logical_connector_calls': connector['logical_connector_calls'],
                                        'site_fetch_reservations': site_checks['site_fetch_reservations'],
                                        'limitations': batch['limitations']})
            for candidate in batch['candidates']:
                name = candidate['repository_full_name']
                meta, readme = metadata[name], readmes[name]
                eid = 'github:repository:' + str(meta['id'])
                owner_id = 'github:owner:' + str(meta['owner']['id'])
                store.entity(owner_id, 'github_owner', str(meta['owner']['id']), meta['owner']['login'], ev)
                store.entity(eid, 'github_repository', str(meta['id']), name, ev,
                             url=meta['html_url'], creator_id=owner_id, availability='public_repository')
                row = {'title': name, 'repo_description': meta.get('description', ''),
                       'topics': meta.get('topics', []), 'body': readme['content']}
                comparison = {'keyword_baseline': score(row, baseline['interests']),
                              'private_facets': score_private(row, private_profile),
                              'evaluation': 'Explanations only; user relevance/novelty and precision are unmeasured.'}
                cid = 'candidate:' + eid
                store.db.execute('INSERT INTO candidates VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(dedupe_key) '
                                 'DO UPDATE SET facets=excluded.facets,reasons=excluded.reasons,'
                                 'uncertainty=excluded.uncertainty,evidence_id=excluded.evidence_id',
                                 (cid, eid, 'open_world', eid, json.dumps(candidate['facets']),
                                  candidate['why'], json.dumps(candidate['limitations']), ev))
                site = sites.get(candidate.get('site_url'), {})
                records.append({**candidate, 'entity_id': eid, 'repository_url': meta['html_url'],
                    'owner_type': meta['owner']['type'], 'archived': meta['archived'],
                    'last_push_reported': meta['pushed_at'], 'readme_blob_sha': readme['sha'],
                    'readme_source': readme['display_url'], 'readme_excerpt_lines': len(readme['content'].splitlines()),
                    'site_check': site.get('site_status', 'not_independently_checked'),
                    'comparison': comparison, 'evidence_id': ev, 'novelty': 'user_familiarity_unknown'})
            prior = {'version': 1, 'visibility': 'private', 'source_snapshot': str(snapshot),
                     'candidates': records, 'limitations': batch['limitations'],
                     'logical_connector_calls': connector['logical_connector_calls'],
                     'site_fetch_reservations': site_checks['site_fetch_reservations'],
                     'failed_connector_calls': sum(bool(r['result'].get('isError')) for r in connector['responses']),
                     'all_candidates_human_evaluated': False}
            store.checkpoint('candidate_batch:' + digest, prior)
    with store.db:
        store.checkpoint('active_candidate_batch', 'candidate_batch:' + digest)
    return write_review_queue(store)


def write_review_queue(store):
    key = store.get_checkpoint('active_candidate_batch')
    if not key:
        raise ValueError('Import an assessed candidate batch before opening its review queue')
    report = store.get_checkpoint(key)
    for item in report['candidates']:
        review = store.db.execute('SELECT decision,reason FROM reviews WHERE entity_id=?', (item['entity_id'],)).fetchone()
        item['review'] = dict(review) if review else {'decision': 'unknown', 'reason': ''}
    private_json(store.folder / 'discovery_queue.json', report)
    h = lambda v: html.escape(str(v if v is not None else ''), quote=True)
    cards = []
    for item in report['candidates']:
        facets = ''.join('<li>' + h(k) + ': ' + h(v) + '</li>' for k, v in item['facets'].items())
        cards.append('<article><h2><a target="_blank" rel="noopener noreferrer" href="' + h(item['repository_url']) +
                     '">' + h(item['repository_full_name']) + '</a></h2><p>' + h(item['why']) +
                     '</p><ul>' + facets + '</ul><p>Owner type: ' + h(item['owner_type']) +
                     ' · Archived: ' + h(str(item['archived'])) + ' · Last push reported: ' + h(item['last_push_reported']) +
                     ' · Site check: ' + h(item['site_check']) + '</p><p>Limits: ' + h(' '.join(item['limitations'])) +
                     '</p><p>Baseline keyword score: ' + h(item['comparison']['keyword_baseline']['score']) +
                     ' · Explicit-interest matches: ' + h(', '.join(m['topic'] for m in item['comparison']['private_facets']['declared_matches'])) +
                     '</p><p>Review: ' + h(item['review']['decision']) + ' ' + h(item['review']['reason']) +
                     '</p><small>Review ID: ' + h(item['entity_id']) + '</small></article>')
    page = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'none'; base-uri 'none'; form-action 'none'">
<title>Private discovery review queue</title><style>body{font:16px system-ui;background:#fafbfc;color:#172b40;margin:2rem;line-height:1.5}main{max-width:1000px;margin:auto}article{background:white;border:1px solid #dde3e9;border-radius:.5rem;padding:1rem;margin:1rem 0}input{font:inherit;padding:.5rem}</style>
<main><h1>First public-project review queue</h1><p>Targeted, manually assessed candidates. Personal usefulness and novelty need your review.
Metadata and README inspection do not establish software correctness or production readiness. No project code was installed or executed.</p>
<label>Filter <input id="filter" type="search"></label>''' + ''.join(cards) + '''
<p>Give keep/later/skip feedback in chat, or use the local review command with the displayed ID. The public catalog remains independent.</p></main>
<script>document.querySelector('#filter').addEventListener('input',e=>{const v=e.target.value.toLowerCase();for(const c of document.querySelectorAll('article'))c.hidden=!c.textContent.toLowerCase().includes(v)});</script></html>'''
    private_write(store.folder / 'discovery_queue.html', page.encode())
    private_json(store.folder / 'evidence_coverage.json', store.coverage())
    return report
