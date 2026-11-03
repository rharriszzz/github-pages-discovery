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
COMPARISONS = ('youtube_only', 'github_only')


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
        comparison = row.get('comparison_kind')
        if comparison and comparison not in COMPARISONS:
            raise ValueError('Unknown single-platform comparison kind')
        if row.get('recommend'):
            platform_counts = (len(row.get('projects', [])), len(row.get('videos', [])))
            valid_works = (0 <= platform_counts[0] <= 3 and 2 <= platform_counts[1] <= 3 if comparison == 'youtube_only' else
                           platform_counts[1] == 0 and 2 <= platform_counts[0] <= 3 if comparison == 'github_only' else
                           all(2 <= n <= 3 for n in platform_counts))
            if ((not comparison and row['identity'] not in ('verified', 'probable')) or
                    (not comparison and not row.get('identity_evidence')) or
                    (comparison == 'youtube_only' and not row.get('youtube_url')) or
                    (comparison == 'github_only' and not row.get('github_url')) or
                    not row.get('why') or not row.get('limitations') or
                    set(row.get('facets', {})) != set(FACETS) or
                    not all(isinstance(row['facets'][k], str) and row['facets'][k] for k in FACETS) or
                    not row.get('interest_links') or not valid_works):
                raise ValueError('Recommendations need verified/probable affiliation or a labeled comparison, eight facets, interest trails and 2..3 works per included platform')
        if row.get('intersection_qualified') and (comparison or row.get('channel_role') != 'operator' or not row.get('recommend') or row['identity'] != 'verified'):
            raise ValueError('Guest presenters cannot be counted as channel-operator intersections')
        for kind in ('projects', 'videos'):
            for work in row.get(kind, []):
                if not safe_url(work.get('url')) or not work.get('title') or not work.get('note'):
                    raise ValueError('Representative works need safe links and bounded inspection notes')
        for trail in row.get('interest_links', []):
            if trail.get('kind') not in ('direct', 'method', 'approach', 'adjacent', 'unexpected') or not trail.get('basis') or not trail.get('candidate_evidence'):
                raise ValueError('Interest connections need a typed, inspectable evidence trail')
            if any(not safe_url(u) for u in trail.get('sources', [])):
                raise ValueError('Connection sources must be safe HTTPS links')
        for concept in row.get('learning_concepts', []):
            if (not concept.get('label') or not concept.get('explanation') or not concept.get('sources') or
                    any(not safe_url(u) for u in concept['sources'])):
                raise ValueError('Learning concepts need explanations and safe source links')


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
                for concept in row.get('learning_concepts', []):
                    concept_id = 'creator-concept:' + hashlib.sha256(concept['label'].casefold().encode()).hexdigest()
                    cev = store.evidence('creator_concept', concept['sources'][0], completeness='partial',
                        notes={'label': concept['label'], 'sources': concept['sources'],
                               'explanation': concept['explanation'], 'novelty': 'awaits_user_review'})
                    store.concept(concept_id, concept['label'], 'method', cev)
                    store.relationship(row['id'], 'explains_or_implements', concept_id, 'known', cev,
                        confidence=0.8, falsification='Withdraw if cited works do not explain or implement this concept.')
                store.db.execute('''INSERT INTO candidates VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(dedupe_key)
                    DO UPDATE SET facets=excluded.facets,reasons=excluded.reasons,
                    uncertainty=excluded.uncertainty,evidence_id=excluded.evidence_id''',
                    (cid, row['id'], 'open_world', row['id'], json.dumps(row.get('facets', {})),
                     row.get('why', row['screening_note']), json.dumps(row.get('limitations', [])), ev))
            report = {**batch, 'visibility': 'private', 'source_snapshot': str(snapshot), 'evidence_id': ev}
            store.checkpoint(key, report)
    with store.db:
        # Migrate only the active pilot, not superseded historical snapshots.
        keys = store.get_checkpoint('creator_collection', [])
        previous = store.get_checkpoint('active_creator_batch')
        for item in (previous, key):
            if item and item not in keys:
                keys.append(item)
        store.checkpoint('creator_collection', keys)
        store.checkpoint('active_creator_batch', key)
    return write_creator_review(store)


def creator_report(store):
    key = store.get_checkpoint('active_creator_batch')
    if not key:
        raise ValueError('Import a creator experiment first')
    keys = store.get_checkpoint('creator_collection', [key])
    batches = [store.get_checkpoint(k) for k in keys]
    report = dict(batches[-1])
    merged = {}
    rounds = []
    for i, batch in enumerate(batches):
        label = batch.get('round_id', 'pilot' if i == 0 else 'expansion')
        rounds.append({'round': label, 'batch': keys[i], 'accounting': batch['accounting'],
                       'investigations': len(batch['investigated'])})
        for row in batch['investigated']:
            item = dict(row)
            item['round_id'] = label
            item['first_round'] = merged.get(row['id'], {}).get('first_round', label)
            merged[row['id']] = item
    report['investigated'] = list(merged.values())
    report['rounds'] = rounds
    report['overall_feedback'] = store.get_checkpoint('creator_overall_feedback', [])
    report['accounting_by_batch'] = rounds
    baseline = json.loads((ROOT / 'data/interests.json').read_text())
    profile_path = store.folder / 'interest_profile.json'
    profile = json.loads(profile_path.read_text()) if profile_path.exists() else baseline
    for row in report['investigated']:
        review = store.db.execute('SELECT decision,reason,updated_at FROM reviews WHERE entity_id=?', (row['id'],)).fetchone()
        row['review'] = dict(review) if review else {'decision': 'unknown', 'reason': '', 'updated_at': None}
        row['review_status'] = 'reviewed' if review else 'unreviewed'
        row.setdefault('discovery_method', 'pilot' if row['first_round'] == 'pilot' else
                       'collection_profile' if row.get('source_observations') else 'related_problem')
        row['connection_group'] = ('unexpected' if any(t['kind'] in ('unexpected', 'adjacent') for t in row.get('interest_links', []))
                                   else 'familiar_interests')
        decision = row['review']['decision']
        row['followup_eligible'] = decision not in ('skip', 'not_interesting', 'already_familiar') or bool(row.get('new_aspect'))
        if decision in ('skip', 'not_interesting'):
            row['followup_eligible'] = False
        text = {'title': row['name'], 'body': ' '.join(x['note'] for x in row.get('projects', [])),
                'topics': row.get('subjects', []) + row.get('methods', [])}
        row['comparison'] = {'keyword_baseline': score(text, baseline['interests']),
                             'private_profile': score_private(text, profile),
                             'human_usefulness': decision if decision in ('very_interesting', 'somewhat_interesting', 'not_interesting') else 'unmeasured'}
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
    report['metrics']['rounds'] = {label: {'investigations': sum(r['first_round'] == label for r in rows),
        'recommendations': sum(bool(r.get('recommend')) and r['first_round'] == label for r in rows),
        'directions': dict(Counter(r['direction'] for r in rows if r['first_round'] == label)),
        'identities': dict(Counter(r['identity'] for r in rows if r['first_round'] == label)),
        'methods': dict(Counter(r.get('discovery_method', 'pilot') for r in rows if r['first_round'] == label))}
        for label in dict.fromkeys(r['first_round'] for r in rows)}
    report['metrics']['single_platform_comparisons'] = dict(Counter(r['comparison_kind'] for r in rows if r.get('recommend') and r.get('comparison_kind')))
    report['metrics']['stages'] = dict(Counter(r.get('investigation_stage', 'pilot_assessment') for r in rows))
    report['metrics']['recommended_subjects'] = dict(Counter(s for r in rows if r.get('recommend') for s in set(r.get('subjects', []))))
    report['metrics']['learning_concepts'] = len({c['label'].casefold() for r in rows for c in r.get('learning_concepts', [])})
    return report


def apply_creator_feedback(store, payload):
    if not isinstance(payload, dict):
        raise ValueError('Feedback must be a JSON object')
    rows = payload.get('reviews')
    allowed = {r['id'] for r in creator_report(store)['investigated']}
    if payload.get('version') != 1 or not isinstance(rows, list) or not 1 <= len(rows) <= 1000:
        raise ValueError('Feedback requires version 1 and 1..1000 reviews')
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
    with store.db:
        for row in rows:
            existing = store.db.execute('SELECT decision,reason FROM reviews WHERE entity_id=?', (row['entity_id'],)).fetchone()
            # Download/import must not turn untouched cards into explicit decisions.
            if not existing and row['decision'] == 'unknown' and not row['reason']:
                continue
            if existing and tuple(existing) == (row['decision'], row['reason']):
                continue
            store.review(row['entity_id'], row['decision'], row['reason'], transaction=False)
    return write_creator_review(store)


def write_creator_review(store):
    report = creator_report(store)
    private_json(store.folder / 'creator_review.json', report)
    private_write(store.folder / 'creator_review.html', render_review(report).encode())
    private_write(store.folder / 'creator_research_report.md', research_report(report).encode())
    private_json(store.folder / 'evidence_coverage.json', store.coverage())
    return report


def research_report(report):
    lines = ['# Private creator pilot and expanded collection', '', report.get('summary', ''), '',
             '## Coverage', '', '```json', json.dumps(report['metrics'], indent=2), '```', '',
             '## Request accounting', '', '```json', json.dumps(report['accounting'], indent=2), '```', '',
             '## Methodology', ''] + ['- ' + x for x in report.get('methodology', [])]
    lines += ['', '## Preserved rounds and request accounting', '', '```json', json.dumps(report.get('rounds', []), indent=2), '```']
    lines += ['', '## Overall user feedback (separate from familiarity)', ''] + [x['statement'] for x in report.get('overall_feedback', [])]
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
                '- ' + t['kind'] + ': ' + t['basis'] + ' → ' + t['candidate_evidence'] +
                ''.join(' [Source](' + u + ')' for u in t.get('sources', []))
                for t in row['interest_links']]
            if row.get('learning_concepts'):
                lines += ['', '### Learning concepts', ''] + [
                    '- ' + c['label'] + ': ' + c['explanation'] +
                    ''.join(' [Source](' + u + ')' for u in c['sources'])
                    for c in row['learning_concepts']]
            lines += ['', '### Uncertainties', ''] + ['- ' + x for x in row['limitations']]
        lines += ['- Evidence: [' + e['url'] + '](' + e['url'] + ') (' + e['retrieved_at'] + '): ' + e['note'] for e in row.get('identity_evidence', [])]
    return '\n'.join(lines) + '\n'


def render_review(report, *, token=''):
    h = lambda x: html.escape(str(x if x is not None else ''), quote=True)
    link = lambda url, label: '<a target="_blank" rel="noopener noreferrer" href="' + h(url) + '">' + h(label) + '</a>' if url and safe_url(url) else h(label)
    recommendations = [r for r in report['investigated'] if r.get('recommend')]
    recommendations.sort(key=lambda r: r.get('first_round', 'pilot') == 'pilot')

    def attributes(row):
        values = {k: row.get(k, '') for k in ('direction', 'identity', 'round_id', 'review_status', 'connection_group')}
        values['platform'] = row.get('comparison_kind', 'cross_platform')
        values['confidence'] = values.pop('identity')
        values.update(subjects=json.dumps(row.get('subjects', [])), methods=json.dumps(row.get('methods', [])))
        return ''.join(' data-' + k.replace('_', '-') + '="' + h(v) + '"' for k, v in values.items())

    groups = {'familiar_interests': ('Familiar interests', 'Direct subjects and shared methods. Creator familiarity remains a separate review.'),
              'unexpected': ('Unexpected discoveries', 'Adjacent and surprising connections, including creators who also match familiar interests.')}
    sections = []
    for group, (title, intro) in groups.items():
        cards = []
        for row in recommendations:
            if row.get('connection_group', 'familiar_interests') != group:
                continue
            works = ''
            for key, label in (('projects', 'Projects'), ('videos', 'Videos / series')):
                if row.get(key):
                    works += '<section><h3>' + label + '</h3><ul>' + ''.join('<li>' + link(w['url'], w['title']) + '<small>' + h(w['note']) + '</small></li>' for w in row[key]) + '</ul></section>'
            evidence = ''.join('<li>' + link(e['url'], e['kind'].replace('_', ' ')) + ': ' + h(e['note']) + '<small>' + h(e['retrieved_at']) + '</small></li>' for e in row.get('identity_evidence', []))
            trails = ''.join('<li><b>' + h(t['kind']) + '</b>: ' + h(t['basis']) + ' → ' + h(t['candidate_evidence']) + ''.join(' · ' + link(u, 'Source') for u in t.get('sources', [])) + '</li>' for t in row['interest_links'])
            facets = ''.join('<div><b>' + h(k.title()) + '</b><p>' + h(v) + '</p></div>' for k, v in row['facets'].items())
            concepts = ('<h3>Learning concepts</h3><ul>' + ''.join(
                '<li><b>' + h(c['label']) + '</b>: ' + h(c['explanation']) +
                ''.join(' · ' + link(u, 'Source') for u in c['sources']) + '</li>'
                for c in row['learning_concepts']) + '</ul>') if row.get('learning_concepts') else ''
            options = ''.join('<option value="' + k + '"' + (' selected' if row['review']['decision'] == k else '') + '>' + v + '</option>' for k, v in DECISIONS.items())
            tags = ' · '.join(row.get('subjects', []) + row.get('methods', []))
            kind = row.get('comparison_kind', 'cross_platform').replace('_', ' ')
            status = row.get('review_status', 'unreviewed')
            cards.append('<article data-id="' + h(row['id']) + '"' + attributes(row) + '><div class="eyebrow">' + h(row.get('first_round', 'pilot')) + ' · <span class="review-status">' + h(status) + '</span> · ' + h(kind) + '</div><h3 class="creator-name">' + h(row['name']) + '</h3><nav>' + link(row.get('youtube_url'), 'YouTube') + ' · ' + link(row.get('github_url'), 'GitHub') + (' · ' + link(row['website'], 'Website') if row.get('website') else '') + '</nav><p>' + h(row['why']) + '</p><p class="tags">' + h(tags) + '</p><details class="work-details"><summary>Representative projects & videos</summary><div class="works">' + works + '</div></details><details><summary>Concepts, assessments & affiliation evidence</summary><p>' + h(row['identity']) + ' cross-platform affiliation · ' + h(row.get('channel_role', 'unconfirmed')) + '</p><div class="facets">' + facets + '</div>' + concepts + '<h3>Interest trail</h3><ul>' + trails + '</ul><h3>Identity / affiliation</h3><ul>' + evidence + '</ul><h3>Uncertainties</h3><ul>' + ''.join('<li>' + h(x) + '</li>' for x in row['limitations']) + '</ul><p>Novel aspect: ' + h(row.get('new_aspect', 'User familiarity unknown.')) + '</p></details><div class="review"><label>Decision <select class="decision">' + options + '</select></label><label class="reasonlabel">Notes <textarea maxlength="4000" rows="2">' + h(row['review']['reason']) + '</textarea></label><button class="save">Save review</button><output aria-live="polite"></output></div></article>')
        sections.append('<section class="collection-group" id="' + group + '"><h2>' + title + '</h2><p>' + intro + '</p>' + ''.join(cards) + '</section>')
    filters = '<label>Search <input id="search" type="search" placeholder="Creator, concept or technique"></label>'
    for key, label, values in [
        ('subject', 'Subject', sorted({s for r in recommendations for s in r.get('subjects', [])})),
        ('method', 'Method', sorted({s for r in recommendations for s in r.get('methods', [])})),
        ('direction', 'Direction', ['youtube_first', 'github_first']), ('confidence', 'Affiliation', list(IDENTITIES)),
        ('roundId', 'Round', list(dict.fromkeys(r.get('round_id', 'pilot') for r in report['investigated']))),
        ('reviewStatus', 'Review', ['unreviewed', 'reviewed']),
        ('platform', 'Platforms', ['cross_platform', 'youtube_only', 'github_only']),
        ('connectionGroup', 'Connection', list(groups))]:
        filters += '<label>' + label + '<select id="' + key + '"><option value="">All</option>' + ''.join('<option value="' + h(v) + '">' + h(v.replace('_', ' ')) + '</option>' for v in values) + '</select></label>'
    table = ''.join('<tr class="investigation"' + attributes(r) + '><td>' + h(r['name']) + '</td><td>' + h(r['direction']) + '</td><td>' + h(r['identity']) + '</td><td>' + h(r['screening_note']) + '</td></tr>' for r in report['investigated'])
    feedback = ''.join('<p class="overall-feedback">' + h(x.get('display', x['statement'])) + '</p>' for x in report.get('overall_feedback', []))
    body = '<header><div class="eyebrow">PRIVATE RESEARCH · CHECKPOINTED COLLECTION</div><h1>Creators, code & ideas</h1><p>' + h(report.get('summary', '')) + '</p>' + feedback + '<p>' + h(report['metrics']['investigations']) + ' investigations · ' + h(len(recommendations)) + ' review candidates. Expanded-round usefulness and concept novelty await your evaluation.</p><p><a href="/" id="refresh">Reload saved reviews</a> · <a class="serverlink" href="/report">Research report</a> · <button id="export">Download feedback</button> <span id="mode"></span></p><nav><a href="#familiar_interests">Familiar interests</a> · <a href="#unexpected">Unexpected discoveries</a></nav></header><div class="filters">' + filters + '<button id="reset-filters">Reset filters</button></div><p id="count" aria-live="polite"></p><main>' + ''.join(sections) + '</main><details class="audit"><summary>All investigations, including exclusions</summary><div class="scroll"><table><thead><tr><th>Creator/channel</th><th>Direction</th><th>Affiliation</th><th>Finding</th></tr></thead><tbody>' + table + '</tbody></table></div><h3>Sample limits</h3><ul>' + ''.join('<li>' + h(x) + '</li>' for x in report['limitations']) + '</ul><pre>' + h(json.dumps(report['metrics'], indent=2)) + '</pre></details>'
    script = Path(__file__).with_name('creator_review.js').read_text()
    css = Path(__file__).with_name('creator_review.css').read_text()
    bootstrap = json.dumps({'token': token, 'reviews': {r['id']: r['review'] for r in recommendations}}).replace('<', '\\u003c')
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; script-src \'unsafe-inline\'; connect-src \'self\'; base-uri \'none\'; form-action \'none\'; frame-src \'none\'"><meta name="referrer" content="no-referrer"><title>Private creator review</title><style>' + css + '</style><body>' + body + '<script>const BOOTSTRAP=' + bootstrap + ';\n' + script + '</script></body></html>'
