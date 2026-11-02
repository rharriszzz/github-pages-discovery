"""Conservative Takeout JSON/HTML history and CSV collection imports.

No archive extraction, guessed locale dates, playback duration or progress inference.
Each selected source is snapshotted before parsing. Unrecognized rows are counted.
"""
from __future__ import annotations

from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import io
import json
import re
from urllib.parse import parse_qs, urlsplit

from .privacy import outside_repo, private_json, private_write
from .research import stable_id

PARSER_VERSION = 1
KINDS = {'history': 'history_seen', 'likes': 'liked', 'watch_later': 'watch_later', 'playlist': 'saved'}
VIDEO_ID = re.compile(r'^[A-Za-z0-9_-]{11}$')
MAX_SOURCE_BYTES = 100_000_000


def video_id(value):
    if not isinstance(value, str):
        return None
    if VIDEO_ID.fullmatch(value):
        return value
    try:
        p = urlsplit(value)
        if p.scheme != 'https' or p.username or p.password:
            return None
        if p.hostname in ('www.youtube.com', 'youtube.com', 'm.youtube.com', 'music.youtube.com'):
            candidate = parse_qs(p.query).get('v', [''])[0] if p.path == '/watch' else (
                p.path.split('/')[2] if p.path.startswith('/shorts/') else '')
        elif p.hostname == 'youtu.be':
            candidate = p.path.strip('/')
        else:
            return None
        return candidate if VIDEO_ID.fullmatch(candidate) else None
    except ValueError:
        return None


def timestamp(value):
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        dt = datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
        if dt.tzinfo is None:
            return None
        return dt.astimezone(timezone.utc).isoformat()
    except ValueError:
        pass
    # Only unambiguous English UTC/GMT timestamps; local abbreviations are not guessed.
    for fmt in ('%b %d, %Y, %I:%M:%S %p UTC', '%b %d, %Y, %I:%M:%S %p GMT',
                '%b %d, %Y, %H:%M:%S UTC', '%Y-%m-%d %H:%M:%S UTC'):
        try:
            return datetime.strptime(value.strip(), fmt).replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            pass
    return None


class HistoryHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.cell = None
        self.rows = []
        self.anchor = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'div':
            self.depth += 1
            if self.cell is None and 'content-cell' in attrs.get('class', '').split():
                self.cell = {'depth': self.depth, 'links': [], 'text': []}
        if self.cell is not None:
            if tag == 'a':
                self.anchor = {'url': attrs.get('href', ''), 'text': []}
            if tag == 'br':
                self.cell['text'].append('\n')

    def handle_data(self, text):
        if self.cell is not None:
            self.cell['text'].append(text)
        if self.anchor is not None:
            self.anchor['text'].append(text)

    def handle_endtag(self, tag):
        if tag == 'a' and self.anchor is not None and self.cell is not None:
            self.cell['links'].append(self.anchor)
            self.anchor = None
        if tag == 'div':
            if self.cell is not None and self.cell['depth'] == self.depth:
                text = ''.join(self.cell['text'])
                links = self.cell['links']
                link = next((a for a in links if video_id(a['url'])), None)
                if link or 'Watched' in text:
                    channel = next((a for a in links if '/channel/' in a['url']), {})
                    self.rows.append({'titleUrl': link['url'] if link else '',
                                      'title': ''.join(link['text']) if link else text.strip(),
                                      'time': next((line.strip() for line in text.splitlines()
                                                    if timestamp(line.strip())), ''),
                                      'subtitles': [{'url': channel.get('url', ''),
                                                    'name': ''.join(channel.get('text', []))}]})
                self.cell = None
            self.depth = max(0, self.depth - 1)


def csv_rows(text):
    rows = list(csv.reader(io.StringIO(text)))
    # Some playlist exports prepend a metadata table before the video table.
    header_at = next((i for i, row in enumerate(rows) if any(
        re.sub(r'[^a-z]', '', c.lower()) in ('videoid', 'videourl') for c in row)), None)
    if header_at is None:
        raise ValueError('CSV has no supported Video ID/Video URL header')
    header = [re.sub(r'[^a-z]', '', c.lower()) for c in rows[header_at]]
    result = []
    for row in rows[header_at + 1:]:
        if not any(row):
            continue
        item = dict(zip(header, row))
        result.append({'titleUrl': item.get('videoid') or item.get('videourl', ''),
                       'title': item.get('title', ''),
                       'time': item.get('time') or item.get('timeadded') or item.get('ratingtimestamp') or
                               item.get('timestamp', '')})
    return result


def import_takeout(store, path, kind, *, playlist_id=None):
    if kind not in KINDS:
        raise ValueError('Unknown Takeout collection kind')
    if kind == 'playlist':
        annotation = store.db.execute('SELECT reviewed FROM playlist_annotations WHERE playlist_id=?',
                                      ('youtube:playlist:' + (playlist_id or ''),)).fetchone()
        if not annotation or not annotation['reviewed']:
            raise ValueError('Review this playlist purpose in the inventory before importing its contents')
    path = outside_repo(path)
    if path.stat().st_size > MAX_SOURCE_BYTES:
        raise ValueError('Source exceeds 100 MB safety bound; split the selected export first')
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    suffix = path.suffix.lower()
    if suffix not in ('.json', '.html', '.csv'):
        raise ValueError('Select an extracted JSON, HTML or CSV file, not an archive')
    snapshot = store.folder / 'sources' / (digest + suffix)
    private_write(snapshot, raw)
    text = raw.decode('utf-8-sig')
    if suffix == '.json':
        rows = json.loads(text)
        if not isinstance(rows, list):
            raise ValueError('Expected a Takeout JSON array')
    elif suffix == '.html':
        if kind != 'history':
            raise ValueError('HTML is supported for watch history only')
        parser = HistoryHTML()
        parser.feed(text)
        rows = parser.rows
        if not rows:
            raise ValueError('No recognized history cells; HTML format/locale may be unsupported')
    else:
        rows = csv_rows(text)
    report = {'version': 1, 'parser_version': PARSER_VERSION, 'visibility': 'private',
              'source_sha256': digest, 'source_snapshot': str(snapshot), 'kind': kind,
              'rows': len(rows), 'imported_observations': 0, 'duplicates': 0,
              'unavailable_or_unrecognized': 0, 'missing_or_ambiguous_time': 0,
              'completeness': 'bounded_export',
              'limitations': ['Export may omit deleted/disabled history and missing periods.',
                             'Saved, liked and Watch Later records are not proof of watching.',
                             'Unavailable/unrecognized rows retained in source snapshot; no IDs invented.',
                             'Unknown/localized timestamps retained as unknown, never guessed.'],
              'watch_minutes': 'not_measurable', 'fractional_completion': 'not_measurable'}
    occurrence = Counter()
    with store.db:
        evidence_id = store.evidence('takeout_' + kind, str(snapshot), completeness='bounded_export',
                                     notes={'sha256': digest, 'parser_version': PARSER_VERSION})
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                report['unavailable_or_unrecognized'] += 1
                continue
            vid = video_id(row.get('titleUrl') or row.get('videoId') or row.get('url'))
            if not vid:
                report['unavailable_or_unrecognized'] += 1
                continue
            observed = timestamp(row.get('time'))
            if not observed:
                report['missing_or_ambiguous_time'] += 1
            title = str(row.get('title') or '').removeprefix('Watched ')
            channel_id = None
            subtitles = row.get('subtitles') if isinstance(row.get('subtitles'), list) else []
            for channel in subtitles:
                if not isinstance(channel, dict):
                    continue
                if not isinstance(channel.get('url'), str):
                    continue
                try:
                    cp = urlsplit(channel['url'])
                except ValueError:
                    continue
                if (cp.scheme == 'https' and cp.hostname in ('www.youtube.com', 'youtube.com') and
                        re.fullmatch(r'/channel/UC[A-Za-z0-9_-]{22}', cp.path)):
                    native = cp.path.rsplit('/', 1)[-1]
                    channel_id = 'youtube:channel:' + native
                    store.entity(channel_id, 'youtube_channel', native, str(channel.get('name') or ''),
                                 evidence_id, url=channel['url'])
                    break
            entity_id = 'youtube:video:' + vid
            store.entity(entity_id, 'youtube_video', vid, title, evidence_id,
                         url='https://www.youtube.com/watch?v=' + vid, creator_id=channel_id)
            key = (KINDS[kind], vid, observed, playlist_id)
            occurrence[key] += 1
            # Across overlapping exports, same timestamp+ID is the same event. Identical
            # repeated rows within a history file remain distinct. Unknown dates cannot
            # be reconciled safely across different exports; retain source identity.
            identity = (key, occurrence[key]) if observed else (key, digest, index)
            if kind != 'history':
                identity = (KINDS[kind], vid, playlist_id)
            inserted = store.observe(stable_id(identity), entity_id, KINDS[kind], observed, evidence_id,
                                     collection=playlist_id, details={'source_row': index,
                                                                    'time_raw': row.get('time'),
                                                                    'time_known': bool(observed)})
            report['imported_observations'] += inserted
            report['duplicates'] += 1 - inserted
        store.checkpoint('takeout:' + kind + ':' + digest, report)
    private_json(store.folder / 'imports' / (kind + '-' + digest + '.json'), report)
    private_json(store.folder / 'evidence_coverage.json', store.coverage())
    return report
