"""Bounded authorized YouTube sources for the shared creator experiment."""
from __future__ import annotations

import json
import re

from .privacy import outside_repo, private_json
from .research import stable_id
from .takeout import timestamp


def import_collection(store, client, *, playlist_id=None, likes=False, max_pages=2):
    if bool(playlist_id) == bool(likes) or not 1 <= max_pages <= 20:
        raise ValueError('Choose one reviewed playlist or Likes and 1..20 pages')
    if playlist_id:
        ann = store.db.execute('SELECT reviewed,relevance FROM playlist_annotations WHERE playlist_id=?',
                               ('youtube:playlist:' + playlist_id,)).fetchone()
        if not ann or not ann['reviewed'] or ann['relevance'] != 'positive':
            raise ValueError('Only explicitly reviewed positive playlists are eligible')
    key = 'creator_source:' + ('likes' if likes else playlist_id)
    state = store.get_checkpoint(key, {'pages': 0, 'next_page': None, 'complete': False,
                                      'items': 0, 'excluded': 0, 'tokens': []})
    try:
        for _ in range(max_pages):
            if state['complete'] or (likes and state['pages'] >= 20):
                break
            params = {'part': 'snippet' if likes else 'snippet,contentDetails', 'maxResults': 50}
            params.update({'myRating': 'like'} if likes else {'playlistId': playlist_id})
            if state['next_page']:
                params['pageToken'] = state['next_page']
            response = client.get('videos' if likes else 'playlistItems', params)
            body = response['body']
            if not isinstance(body.get('items'), list):
                raise ValueError('YouTube collection response lacks an item list')
            next_page = body.get('nextPageToken')
            if next_page and next_page in state['tokens']:
                raise ValueError('Repeated pagination token; stopping collection')
            with store.db:
                ev = store.evidence('youtube_likes' if likes else 'youtube_curated_playlist', key,
                    completeness='partial', notes={'page': state['pages'], 'cached_at': response['fetched'],
                    'limit': 'Recent Likes max 1000; saved/liked does not establish viewing or endorsement.'})
                for item in body['items']:
                    sn = item.get('snippet', {})
                    vid = item.get('id') if likes else item.get('contentDetails', {}).get('videoId')
                    channel = sn.get('channelId') if likes else sn.get('videoOwnerChannelId')
                    if not isinstance(vid, str) or not re.fullmatch(r'[\w-]{11}', vid):
                        state['excluded'] += 1
                        continue
                    creator_id = None
                    if isinstance(channel, str) and re.fullmatch(r'UC[\w-]{22}', channel):
                        creator_id = 'youtube:channel:' + channel
                        title = sn.get('channelTitle') if likes else sn.get('videoOwnerChannelTitle')
                        store.entity(creator_id, 'youtube_channel', channel, title or '', ev,
                                     url='https://www.youtube.com/channel/' + channel)
                    eid = 'youtube:video:' + vid
                    store.entity(eid, 'youtube_video', vid, sn.get('title', ''), ev,
                                 url='https://www.youtube.com/watch?v=' + vid, creator_id=creator_id,
                                 published_at=timestamp(sn.get('publishedAt')) if likes else None)
                    kind = 'liked' if likes else 'saved'
                    store.observe(stable_id((kind, vid, playlist_id)), eid, kind,
                        None if likes else timestamp(sn.get('publishedAt')), ev, collection=playlist_id,
                        details={'description': sn.get('description', ''), 'source': key,
                                 'rating_time': 'unknown' if likes else 'not_applicable'})
                    state['items'] += 1
                state['pages'] += 1
                state['next_page'] = next_page
                state['complete'] = not bool(next_page)
                if next_page:
                    state['tokens'].append(next_page)
                store.checkpoint(key, state)
    finally:
        private_json(store.folder / 'creator_source_coverage.json', {
            'visibility': 'private', 'collections': [dict(key=r[0], state=json.loads(r[1]))
                for r in store.db.execute("SELECT key,value FROM checkpoints WHERE key LIKE 'creator_source:%'")],
            'last_invocation': {'api_attempts': client.requests, 'cache_hits': client.cache_hits},
            'budget_usage': client.state.usage()})
    return state


def channel_seeds(store):
    """No popularity weighting. Retain source rows and all screened-out channels."""
    rows = store.db.execute('''SELECT e.creator_id, c.native_id, c.title, e.title video_title,
        e.canonical_url video_url, o.kind, o.collection_id, o.details, o.evidence_id
        FROM observations o JOIN entities e ON e.id=o.entity_id
        JOIN entities c ON c.id=e.creator_id
        WHERE o.kind IN ('liked','saved') AND c.kind='youtube_channel'
        ORDER BY c.id, e.id''')
    channels = {}
    for row in rows:
        item = channels.setdefault(row['creator_id'], {'entity_id': row['creator_id'],
            'channel_id': row['native_id'], 'name': row['title'], 'sources': []})
        item['sources'].append({k: row[k] for k in ('video_title', 'video_url', 'kind', 'collection_id', 'evidence_id')})
    report = {'version': 1, 'visibility': 'private', 'channels': list(channels.values()),
              'limitations': ['A saved/liked video establishes encounter evidence, not familiarity or proficiency.',
                             'Recent bounded Likes and selected playlists are a targeted, incomplete sample.']}
    private_json(store.folder / 'creator_seeds.json', report)
    return report


def inspect_metadata(store, client, source):
    """Explicit bounded IDs only; shared response cache makes repeat runs offline."""
    path = outside_repo(source)
    if path.stat().st_size > 100_000:
        raise ValueError('Metadata selection exceeds bound')
    selection = json.loads(path.read_text())
    if not isinstance(selection, dict):
        raise ValueError('Metadata selection must be a JSON object')
    channels, videos, handles = (selection.get(k, []) for k in ('channels', 'videos', 'handles'))
    uploads = selection.get('uploads', [])
    if any(not isinstance(x, list) for x in (channels, videos, handles)) or len(channels) > 60 or len(videos) > 180 or len(handles) > 15:
        raise ValueError('Select at most 60 channels, 180 videos and 15 handles per batch')
    if any(not isinstance(v, str) or not re.fullmatch(r'UC[\w-]{22}', v) for v in channels):
        raise ValueError('Invalid channel ID')
    if any(not isinstance(v, str) or not re.fullmatch(r'[\w-]{11}', v) for v in videos):
        raise ValueError('Invalid video ID')
    if any(not isinstance(v, str) or not re.fullmatch(r'@?[\w.-]{1,100}', v) for v in handles):
        raise ValueError('Invalid channel handle')
    report = store.get_checkpoint('creator_metadata', {'version': 1, 'visibility': 'private',
                                                      'channels': {}, 'videos': {}})
    if not isinstance(uploads, list) or len(uploads) > 15 or any(c not in report['channels'] for c in uploads):
        raise ValueError('Upload sampling needs at most 15 previously inspected channel IDs')
    report.setdefault('uploads', {})
    requests = []
    for resource, values in (('channels', channels), ('videos', videos)):
        for i in range(0, len(values), 50):
            requests.append((resource, {'part': 'snippet,contentDetails', 'id': ','.join(values[i:i+50])}))
    requests.extend(('channels', {'part': 'snippet,contentDetails', 'forHandle': h}) for h in handles)
    for channel in uploads:
        playlist = report['channels'][channel]['item'].get('contentDetails', {}).get('relatedPlaylists', {}).get('uploads')
        if not playlist:
            raise ValueError('Channel has no cached upload playlist')
        requests.append(('playlistItems', {'part': 'snippet,contentDetails', 'playlistId': playlist, 'maxResults': 10}))
    try:
        for resource, params in requests:
            response = client.get(resource, params)
            if not isinstance(response['body'].get('items'), list):
                raise ValueError('Metadata response lacks items')
            with store.db:
                if resource == 'playlistItems':
                    channel = next(c for c in uploads if report['channels'][c]['item']['contentDetails']['relatedPlaylists']['uploads'] == params['playlistId'])
                    report['uploads'][channel] = {'items': response['body']['items'], 'fetched_at': response['fetched'],
                                                 'scope': 'At most ten currently listed uploads; not a complete catalog.'}
                else:
                    for item in response['body']['items']:
                        report[resource][item['id']] = {'item': item, 'fetched_at': response['fetched']}
                store.checkpoint('creator_metadata', report)
    finally:
        report['last_invocation'] = {'api_attempts': client.requests, 'cache_hits': client.cache_hits}
        private_json(store.folder / 'creator_metadata.json', report)
    return report
