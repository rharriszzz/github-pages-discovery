"""Private cross-platform experiments on the existing evidence/queue/review store."""
from __future__ import annotations

from collections import Counter
import hashlib
import html
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from .core import ROOT, score
from .interests import score_private
from .privacy import outside_repo, private_json, private_write
from .research import now

IDENTITIES = ('verified', 'probable', 'uncertain', 'no_match')
DECISIONS = {'unknown': 'Unreviewed', 'already_familiar': 'Already familiar',
             'very_interesting': 'Very interesting', 'somewhat_interesting': 'Somewhat interesting',
             'not_interesting': 'Not interesting', 'investigate_later': 'Investigate later'}
FACETS = ('relevance', 'depth', 'originality', 'clarity', 'breadth', 'novelty', 'activity', 'confidence')


def safe_url(url):
    try:
        p = urlsplit(url)
        return p.scheme == 'https' and bool(p.hostname) and not p.username and not p.password
    except (ValueError, TypeError):
        return False


def _read(path):
    path = outside_repo(path)
    if path.stat().st_size > 20_000_000:
        raise ValueError('Creator source exceeds 20 MB bound')
    return path.read_bytes()


def validate_batch(batch):
    if not isinstance(batch, dict):
        raise ValueError('Creator experiment must be a JSON object')
    rows = batch.get('investigated')
    if batch.get('version') != 1 or not isinstance(rows, list) or not 1 <= len(rows) <= 75:
        raise ValueError('Creator experiments require version 1 and 1..75 investigated records')
    if not batch.get('limitations') or not isinstance(batch.get('accounting'), dict):
        raise ValueError('Experiments require limitations and explicit request accounting')
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('Creator investigations must be objects')
        if not re.fullmatch(r'[A-Za-z0-9:_-]{1,150}', row.get('id', '')) or row['id'] in seen:
            raise ValueError('Creator IDs must be unique, stable and namespaced')
        seen.add(row['id'])
        if (row.get('direction') not in ('youtube_first', 'github_first') or
                row.get('origin') not in ('existing_interest', 'exploratory') or
                row.get('identity') not in IDENTITIES or not row.get('screening_note')):
            raise ValueError('Each investigation needs direction, origin, identity and screening rationale')
        for key in ('youtube_url', 'github_url', 'website'):
            if row.get(key) and not safe_url(row[key]):
                raise ValueError('Creator links must be credential-free HTTPS URLs')
        for account in row.get('accounts', []):
            if (account.get('kind') not in ('github_owner', 'youtube_channel') or
                    not account.get('id') or not account.get('native_id') or
                    not account.get('title') or not safe_url(account.get('url'))):
                raise ValueError('Accounts need separate stable identities and safe links')
        evidence = row.get('identity_evidence', [])
        for item in evidence:
            if not safe_url(item.get('url')) or not item.get('retrieved_at') or not item.get('note'):
                raise ValueError('Identity evidence needs a safe URL, retrieval date and observation')
            try:
                from datetime import datetime
                if datetime.fromisoformat(item['retrieved_at'].replace('Z', '+00:00')).tzinfo is None:
                    raise ValueError()
            except (ValueError, TypeError):
                raise ValueError('Evidence dates must be timezone-aware ISO timestamps') from None
        if row['identity'] == 'verified' and (not row.get('youtube_url') or not row.get('github_url') or not any(
                e.get('kind') in ('official_self_link', 'official_project_affiliation') and
                e.get('relationship') in ('owner', 'maintainer', 'organization_affiliation', 'presenter') for e in evidence)):
            raise ValueError('Verified identity requires explicit official affiliation, never a name or citation alone')
        if row.get('recommend'):
            if (row['identity'] != 'verified' or not row.get('why') or not row.get('limitations') or
                    set(row.get('facets', {})) != set(FACETS) or
                    not all(isinstance(row['facets'][k], str) and row['facets'][k] for k in FACETS) or
                    not row.get('interest_links') or not 2 <= len(row.get('projects', [])) <= 3 or
                    not 2 <= len(row.get('videos', [])) <= 3):
                raise ValueError('Recommendations need verified affiliation, eight evidence facets, interest trails and 2..3 works per platform')
        if row.get('intersection_qualified') and (row.get('channel_role') != 'operator' or not row.get('recommend')):
            raise ValueError('Guest presenters cannot be counted as channel-operator intersections')
        for kind in ('projects', 'videos'):
            for work in row.get(kind, []):
                if not safe_url(work.get('url')) or not work.get('title') or not work.get('note'):
                    raise ValueError('Representative works need safe links and bounded inspection notes')
        for trail in row.get('interest_links', []):
            if trail.get('kind') not in ('direct', 'method', 'approach', 'adjacent', 'unexpected') or not trail.get('basis') or not trail.get('candidate_evidence'):
                raise ValueError('Interest connections need a typed, inspectable evidence trail')


def import_creator_batch(store, source):
    source = outside_repo(source)
    raw = _read(source)
    batch = json.loads(raw)
    validate_batch(batch)
    artifacts = {}
    for name in batch.get('artifacts', []):
        path = (source.parent / name).resolve()
        if not path.is_relative_to(source.parent) or path == source:
            raise ValueError('Research artifacts must stay beside the selected manifest')
        artifacts[name] = json.loads(_read(path))
    digest = hashlib.sha256(raw + json.dumps(artifacts, sort_keys=True).encode()).hexdigest()
    key = 'creator_batch:' + digest
    if not store.get_checkpoint(key):
        snapshot = store.folder / 'sources' / ('creator-batch-' + digest + '.json')
        private_json(snapshot, {'visibility': 'private', 'batch': batch, 'artifacts': artifacts})
        with store.db:
            ev = store.evidence('cross_platform_creator_pilot', str(snapshot), completeness='partial',
                notes={'identity_policy': 'Explicit links; references are not identity.', 'accounting': batch['accounting']})
            for row in batch['investigated']:
                store.entity(row['id'], 'creator_candidate', row['id'], row['name'], ev,
                             url=row.get('youtube_url') or row.get('github_url', ''))
                # Accounts remain separate objects; affiliations never merge their identities.
                for account in row.get('accounts', []):
                    store.entity(account['id'], account['kind'], account['native_id'], account['title'], ev,
                                 url=account['url'])
                    if row['identity'] == 'verified':
                        store.relationship(row['id'], 'affiliated_with', account['id'], 'known', ev,
                            confidence=1.0, falsification='Withdraw if official affiliation is corrected or evidence was a citation.')
                for trail in row.get('interest_links', []):
                    target = trail.get('entity_id')
                    if target and store.db.execute('SELECT 1 FROM entities WHERE id=?', (target,)).fetchone():
                        store.relationship(row['id'], 'candidate_' + trail['kind'] + '_connection', target,
                            'hypothesis', ev, confidence=0.5,
                            falsification='Reject if user feedback disputes this proposed connection; no proficiency inferred.')
                cid = 'candidate:' + row['id']
                store.db.execute('''INSERT INTO candidates VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(dedupe_key)
                    DO UPDATE SET facets=excluded.facets,reasons=excluded.reasons,
                    uncertainty=excluded.uncertainty,evidence_id=excluded.evidence_id''',
                    (cid, row['id'], 'open_world', row['id'], json.dumps(row.get('facets', {})),
                     row.get('why', row['screening_note']), json.dumps(row.get('limitations', [])), ev))
            report = {**batch, 'visibility': 'private', 'source_snapshot': str(snapshot), 'evidence_id': ev}
            store.checkpoint(key, report)
    with store.db:
        store.checkpoint('active_creator_batch', key)
    return write_creator_review(store)


def creator_report(store):
    key = store.get_checkpoint('active_creator_batch')
    if not key:
        raise ValueError('Import a creator experiment first')
    report = store.get_checkpoint(key)
    baseline = json.loads((ROOT / 'data/interests.json').read_text())
    profile_path = store.folder / 'interest_profile.json'
    profile = json.loads(profile_path.read_text()) if profile_path.exists() else baseline
    for row in report['investigated']:
        review = store.db.execute('SELECT decision,reason,updated_at FROM reviews WHERE entity_id=?', (row['id'],)).fetchone()
        row['review'] = dict(review) if review else {'decision': 'unknown', 'reason': '', 'updated_at': None}
        decision = row['review']['decision']
        row['followup_eligible'] = decision not in ('skip', 'not_interesting', 'already_familiar') or bool(row.get('new_aspect'))
        if decision in ('skip', 'not_interesting'):
            row['followup_eligible'] = False
        text = {'title': row['name'], 'body': ' '.join(x['note'] for x in row.get('projects', [])),
                'topics': row.get('subjects', []) + row.get('methods', [])}
        row['comparison'] = {'keyword_baseline': score(text, baseline['interests']),
                             'private_profile': score_private(text, profile),
                             'human_usefulness': 'unmeasured' if decision == 'unknown' else decision}
    rows = report['investigated']
    directions = {}
    for direction in ('youtube_first', 'github_first'):
        cohort = [r for r in rows if r['direction'] == direction]
        directions[direction] = {'investigations': len(cohort),
            'identities': dict(Counter(r['identity'] for r in cohort)),
            'substantial_relevant_work': sum(bool(r.get('substantial_relevant_work')) for r in cohort),
            'recommendations': sum(bool(r.get('recommend')) for r in cohort)}
        directions[direction]['intersection_qualified'] = sum(bool(r.get('intersection_qualified')) for r in cohort)
    report['metrics'] = {'directions': directions, 'identities': dict(Counter(r['identity'] for r in rows)),
        'investigations': len(rows), 'youtube_channels_examined': len({r['youtube_url'] for r in rows if r.get('youtube_url')}),
        'github_accounts_examined': len({a['url'] for r in rows for a in r.get('accounts', []) if a['kind'] == 'github_owner'}),
        'origins': dict(Counter(r['origin'] for r in rows)),
        'recommendations': sum(bool(r.get('recommend')) for r in rows),
        'reviews': dict(Counter(r['review']['decision'] for r in rows if r.get('recommend')))}
    report['metrics']['intersection_qualified'] = sum(bool(r.get('intersection_qualified')) for r in rows)
    report['metrics']['acquisition_channels_examined'] = len(report.get('channel_checks', []))
    report['metrics']['all_github_accounts_examined'] = len(report.get('account_checks', []))
    return report


def apply_creator_feedback(store, payload):
    if not isinstance(payload, dict):
        raise ValueError('Feedback must be a JSON object')
    rows = payload.get('reviews')
    allowed = {r['id'] for r in creator_report(store)['investigated']}
    if payload.get('version') != 1 or not isinstance(rows, list) or not 1 <= len(rows) <= 75:
        raise ValueError('Feedback requires version 1 and 1..75 reviews')
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('Feedback rows must be objects')
        if (row.get('entity_id') not in allowed or row['entity_id'] in seen or
                row.get('decision') not in DECISIONS or not isinstance(row.get('reason'), str) or
                len(row['reason']) > 4000):
            raise ValueError('Invalid creator review ID, decision or explanation')
        seen.add(row['entity_id'])
    # A complete payload validates before any durable feedback changes.
    for row in rows:
        store.review(row['entity_id'], row['decision'], row['reason'])
    return write_creator_review(store)


def write_creator_review(store):
    report = creator_report(store)
    private_json(store.folder / 'creator_review.json', report)
    private_write(store.folder / 'creator_review.html', render_review(report).encode())
    private_write(store.folder / 'creator_research_report.md', research_report(report).encode())
    private_json(store.folder / 'evidence_coverage.json', store.coverage())
    return report


def research_report(report):
    lines = ['# Private creator pilot', '', report.get('summary', ''), '',
             '## Coverage', '', '```json', json.dumps(report['metrics'], indent=2), '```', '',
             '## Request accounting', '', '```json', json.dumps(report['accounting'], indent=2), '```', '',
             '## Methodology', ''] + ['- ' + x for x in report.get('methodology', [])]
    lines += ['', '## Direction comparison', ''] + report.get('direction_analysis', [])
    lines += ['', '## False positives and unproductive paths', ''] + ['- ' + x for x in report.get('false_positives', [])]
    lines += ['', '## Limitations', ''] + ['- ' + x for x in report['limitations']]
    lines += ['', '## Next experiment', ''] + ['- ' + x for x in report.get('next_experiment', [])]
    lines += ['', '## Connections (never identity equivalences)', ''] + [
        '- ' + e['subject'] + ' → ' + e['predicate'] + ' → ' + e['object'] + ': ' + e['evidence']
        for e in report.get('connections', [])]
    for row in report['investigated']:
        lines.extend(['', '## ' + row['name'], '', row['direction'] + ' / ' + row['identity'], '', row['screening_note']])
        if row.get('recommend'):
            lines += ['', row['why'], ''] + ['- ' + k + ': ' + v for k, v in row['facets'].items()]
            for kind in ('projects', 'videos'):
                lines += ['', '### ' + kind.title(), ''] + [
                    '- [' + w['title'] + '](' + w['url'] + '): ' + w['note'] for w in row[kind]]
            lines += ['', '### Interest trail', ''] + [
                '- ' + t['kind'] + ': ' + t['basis'] + ' → ' + t['candidate_evidence']
                for t in row['interest_links']]
        lines += ['- Evidence: [' + e['url'] + '](' + e['url'] + ') (' + e['retrieved_at'] + '): ' + e['note'] for e in row.get('identity_evidence', [])]
    return '\n'.join(lines) + '\n'


def render_review(report, *, token=''):
    h = lambda x: html.escape(str(x if x is not None else ''), quote=True)
    link = lambda url, label: '<a target="_blank" rel="noopener noreferrer" href="' + h(url) + '">' + h(label) + '</a>' if url and safe_url(url) else h(label)
    cards = []
    recommendations = [r for r in report['investigated'] if r.get('recommend')]
    for row in recommendations:
        works = ''
        for key, label in (('projects', 'Projects'), ('videos', 'Videos / series')):
            works += '<section><h3>' + label + '</h3><ul>' + ''.join('<li>' + link(w['url'], w['title']) + ' <small>' + h(w['note']) + '</small></li>' for w in row[key]) + '</ul></section>'
        evidence = ''.join('<li>' + link(e['url'], e['kind'].replace('_', ' ')) + ': ' + h(e['note']) + ' <small>' + h(e['retrieved_at']) + '</small></li>' for e in row['identity_evidence'])
        trails = ''.join('<li><b>' + h(t['kind']) + '</b>: ' + h(t['basis']) + ' → ' + h(t['candidate_evidence']) + '</li>' for t in row['interest_links'])
        facets = ''.join('<div><b>' + h(k.title()) + '</b><p>' + h(v) + '</p></div>' for k, v in row['facets'].items())
        options = ''.join('<option value="' + k + '"' + (' selected' if row['review']['decision'] == k else '') + '>' + v + '</option>' for k, v in DECISIONS.items())
        tags = ' · '.join(row.get('subjects', []) + row.get('methods', []))
        cards.append('<article data-id="' + h(row['id']) + '" data-direction="' + h(row['direction']) + '" data-confidence="' + h(row['identity']) + '" data-subjects="' + h(json.dumps(row.get('subjects', []))) + '" data-methods="' + h(json.dumps(row.get('methods', []))) + '"><div class="eyebrow">' + h(row['direction'].replace('_', ' ')) + ' · ' + h(row['identity']) + ' affiliation · ' + h(row.get('channel_role', 'operator')) + '</div><h2>' + h(row['name']) + '</h2><nav>' + link(row.get('youtube_url'), 'YouTube') + ' · ' + link(row.get('github_url'), 'GitHub') + (' · ' + link(row['website'], 'Website') if row.get('website') else '') + '</nav><p>' + h(row['why']) + '</p><p class="tags">' + h(tags) + '</p><div class="works">' + works + '</div><details><summary>Assessments, interest trail & identity evidence</summary><div class="facets">' + facets + '</div><h3>Interest trail</h3><ul>' + trails + '</ul><h3>Identity / affiliation</h3><ul>' + evidence + '</ul><h3>Uncertainties</h3><ul>' + ''.join('<li>' + h(x) + '</li>' for x in row['limitations']) + '</ul><p>Novel aspect: ' + h(row.get('new_aspect', 'User familiarity unknown.')) + '</p><p>Keyword baseline: ' + h(row['comparison']['keyword_baseline']['score']) + '; profile comparison is triage only. No combined creator score.</p></details><div class="review"><label>Decision <select class="decision">' + options + '</select></label><label class="reasonlabel">Why? <textarea maxlength="4000" rows="2">' + h(row['review']['reason']) + '</textarea></label><button class="save">Save review</button><output aria-live="polite"></output></div></article>')
    filters = '<label>Search <input id="search" type="search" placeholder="Creator, concept or technique"></label>'
    for key, label, values in [('subject', 'Subject', sorted({s for r in recommendations for s in r.get('subjects', [])})), ('method', 'Method', sorted({s for r in recommendations for s in r.get('methods', [])})), ('direction', 'Direction', ['youtube_first', 'github_first']), ('confidence', 'Identity', list(IDENTITIES))]:
        filters += '<label>' + label + '<select id="' + key + '"><option value="">All</option>' + ''.join('<option value="' + h(v) + '">' + h(v.replace('_', ' ')) + '</option>' for v in values) + '</select></label>'
    table = ''.join('<tr class="investigation" data-direction="' + h(r['direction']) + '" data-confidence="' + h(r['identity']) + '" data-subjects="' + h(json.dumps(r.get('subjects', []))) + '" data-methods="' + h(json.dumps(r.get('methods', []))) + '"><td>' + h(r['name']) + '</td><td>' + h(r['direction']) + '</td><td>' + h(r['identity']) + '</td><td>' + h(r['screening_note']) + '</td></tr>' for r in report['investigated'])
    body = '<header><div class="eyebrow">PRIVATE RESEARCH · BOUNDED PILOT</div><h1>Creators, code & ideas</h1><p>' + h(report.get('summary', '')) + '</p><p>' + h(str(report['metrics']['investigations'])) + ' investigations · ' + h(str(len(recommendations))) + ' review candidates · usefulness and novelty await your decisions.</p><p><a href="/" id="refresh">Reload saved reviews</a> · <a class="serverlink" href="/report">Research report</a> · <button id="export">Download feedback</button> <span id="mode"></span></p></header><div class="filters">' + filters + '</div><p id="count" aria-live="polite"></p><main>' + ''.join(cards) + '</main><details class="audit"><summary>All investigations, including exclusions</summary><div class="scroll"><table><thead><tr><th>Creator/channel</th><th>Direction</th><th>Identity</th><th>Finding</th></tr></thead><tbody>' + table + '</tbody></table></div><h3>Sample limits</h3><ul>' + ''.join('<li>' + h(x) + '</li>' for x in report['limitations']) + '</ul><pre>' + h(json.dumps(report['metrics'], indent=2)) + '</pre></details>'
    script = (Path(__file__).with_name('creator_review.js')).read_text()
    css = (Path(__file__).with_name('creator_review.css')).read_text()
    bootstrap = json.dumps({'token': token, 'reviews': {r['id']: r['review'] for r in recommendations}}).replace('<', '\\u003c')
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; script-src \'unsafe-inline\'; connect-src \'self\'; base-uri \'none\'; form-action \'none\'; frame-src \'none\'"><meta name="referrer" content="no-referrer"><title>Private creator review</title><style>' + css + '</style><body>' + body + '<script>const BOOTSTRAP=' + bootstrap + ';\n' + script + '</script></body></html>'
