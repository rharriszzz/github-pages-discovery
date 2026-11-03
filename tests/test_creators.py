from copy import deepcopy
import http.client
import json
from pathlib import Path
import re
import tempfile
import threading
import unittest
from unittest.mock import patch

from pagefinder.creator_server import make_server
from pagefinder.creator_sources import import_collection, inspect_metadata
from pagefinder.creators import (apply_creator_feedback, creator_report, import_creator_batch,
                                 render_review, validate_batch)
from pagefinder.net import BudgetExceeded
from pagefinder.research import Store
from pagefinder.youtube import YouTubeClient


def batch():
    return {'version': 1, 'limitations': ['Synthetic targeted sample'], 'accounting': {'youtube_units': 0},
        'investigated': [{'id': 'creator:synthetic', 'name': '<Synthetic>', 'direction': 'github_first',
            'origin': 'exploratory', 'identity': 'verified', 'screening_note': 'Synthetic official project link',
            'youtube_url': 'https://www.youtube.com/channel/synthetic', 'github_url': 'https://github.com/synthetic',
            'recommend': True, 'substantial_relevant_work': True, 'subjects': ['Geometry'], 'methods': ['Proof'],
            'identity_evidence': [{'url': 'https://github.com/synthetic/project', 'retrieved_at': '2026-11-02T12:00:00Z',
                'kind': 'official_self_link', 'relationship': 'owner', 'note': 'Synthetic own-channel link'}],
            'projects': [{'title': 'Synthetic project ' + str(i), 'url': 'https://github.com/synthetic/project' + str(i),
                          'note': 'Synthetic geometry example'} for i in range(2)],
            'videos': [{'title': 'Synthetic video ' + str(i), 'url': 'https://www.youtube.com/watch?v=synthetic' + str(i),
                        'note': 'Synthetic explanation'} for i in range(2)],
            'why': 'Synthetic methodological connection', 'limitations': ['Not executed'],
            'facets': {k: 'Synthetic bounded evidence' for k in ('relevance','depth','originality','clarity','breadth','novelty','activity','confidence')},
            'interest_links': [{'kind': 'method', 'basis': 'Synthetic graph subject', 'candidate_evidence': 'Synthetic project'}]}]}


class CreatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.store = Store(self.folder / 'private')
        self.source = self.folder / 'batch.json'
        self.source.write_text(json.dumps(batch()))

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_references_and_name_matches_never_establish_verified_identity(self):
        for kind, relation in [('same_name', 'owner'), ('official_self_link', 'cites'), ('third_party', 'owner')]:
            data = batch()
            data['investigated'][0]['identity_evidence'][0].update(kind=kind, relationship=relation)
            with self.assertRaises(ValueError):
                validate_batch(data)
        data = batch()
        data['investigated'][0].update(identity='uncertain', recommend=False)
        validate_batch(data)
        data = batch()
        data['investigated'][0].update(intersection_qualified=True, channel_role='guest presenter')
        with self.assertRaises(ValueError): validate_batch(data)

    def test_sample_denominators_and_separate_facets_survive_feedback_and_reimport(self):
        with patch('socket.create_connection', side_effect=AssertionError('offline import')):
            report = import_creator_batch(self.store, self.source)
        self.assertEqual(report['metrics']['recommendations'], 1)
        self.assertEqual(report['metrics']['directions']['github_first']['investigations'], 1)
        counts = self.store.coverage()['counts']
        apply_creator_feedback(self.store, {'version': 1, 'reviews': [{'entity_id': 'creator:synthetic',
            'decision': 'already_familiar', 'reason': 'Synthetic note'}]})
        report = import_creator_batch(self.store, self.source)
        self.assertEqual(report['investigated'][0]['review']['reason'], 'Synthetic note')
        self.assertFalse(report['investigated'][0]['followup_eligible'])
        self.assertEqual(counts['candidates'], self.store.coverage()['counts']['candidates'])
        self.assertEqual(len(report['investigated'][0]['facets']), 8)
        self.assertEqual(self.store.db.execute('PRAGMA user_version').fetchone()[0], 1)
        for name in ('creator_review.html','creator_review.json','creator_research_report.md'):
            self.assertEqual((self.store.folder / name).stat().st_mode & 0o777, 0o600)

    def test_feedback_validation_precedes_all_writes_and_explicit_skip_overrides_novel_aspect(self):
        import_creator_batch(self.store, self.source)
        payload = {'version':1,'reviews':[{'entity_id':'creator:synthetic','decision':'very_interesting','reason':'x'},
                                          {'entity_id':'unknown','decision':'very_interesting','reason':'x'}]}
        with self.assertRaises(ValueError):
            apply_creator_feedback(self.store, payload)
        self.assertEqual(self.store.coverage()['counts']['reviews'], 0)
        payload['reviews'] = [dict(payload['reviews'][0], decision='not_interesting')]
        report = apply_creator_feedback(self.store, payload)
        self.assertFalse(report['investigated'][0]['followup_eligible'])

    def test_import_rejects_unsafe_urls_dates_missing_work_and_artifact_escape(self):
        for change in ('url','date','works','facets','artifacts'):
            data = batch(); row = data['investigated'][0]
            if change == 'url': row['videos'][0]['url'] = 'javascript:alert(1)'
            if change == 'date': row['identity_evidence'][0]['retrieved_at'] = '2026-11-02'
            if change == 'works': row['projects'] = row['projects'][:1]
            if change == 'facets': del row['facets']['originality']
            if change == 'artifacts': data['artifacts'] = ['../escape.json']
            self.source.write_text(json.dumps(data))
            with self.assertRaises(ValueError): import_creator_batch(self.store, self.source)
        self.assertEqual(self.store.coverage()['counts']['candidates'], 0)

    def test_html_escapes_source_text_and_script_bootstrap(self):
        data = batch(); data['investigated'][0]['name'] = '</script><img src=x onerror=alert(1)>'
        self.source.write_text(json.dumps(data))
        report = import_creator_batch(self.store, self.source)
        page = render_review(report, token='synthetic')
        self.assertNotIn('<img src=x', page)
        self.assertIn('&lt;/script&gt;', page)
        self.assertIn("frame-src 'none'", page)
        self.assertIn('no-referrer', page)

    def test_loopback_server_saves_durably_and_rejects_foreign_origins_and_paths(self):
        import_creator_batch(self.store, self.source)
        server = make_server(self.store.folder, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        conn = http.client.HTTPConnection('127.0.0.1', server.server_port)
        try:
            conn.request('GET', '/'); response = conn.getresponse(); page = response.read().decode()
            self.assertEqual(response.status, 200)
            token = re.search(r'const BOOTSTRAP=(.*);\n', page).group(1)
            token = json.loads(token)['token']
            conn.request('GET', '/report'); report_response = conn.getresponse()
            self.assertEqual(report_response.status, 200)
            self.assertIn('Private creator pilot', report_response.read().decode())
            body = json.dumps({'version':1,'reviews':[{'entity_id':'creator:synthetic','decision':'very_interesting','reason':'Durable synthetic'}]})
            headers = {'Content-Type':'application/json','Origin':f'http://127.0.0.1:{server.server_port}', 'X-Review-Token':token}
            conn.request('POST','/api/review',body,headers); response=conn.getresponse(); response.read()
            self.assertEqual(response.status,200)
            self.assertEqual(creator_report(self.store)['investigated'][0]['review']['reason'],'Durable synthetic')
            headers['Origin']='https://untrusted.example'
            conn.request('POST','/api/review',body,headers); response=conn.getresponse();response.read()
            self.assertEqual(response.status,403)
            conn.request('GET','/research.sqlite3'); response=conn.getresponse();response.read()
            self.assertEqual(response.status,404)
            conn.request('GET','/',headers={'Host':'untrusted.example'});response=conn.getresponse();response.read()
            self.assertEqual(response.status,403)
        finally:
            conn.close();server.shutdown();server.server_close();thread.join()


class CreatorSourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.folder=Path(self.tmp.name)
        self.store=Store(self.folder/'private'); self.calls=[];self.time=1700000000.0
        self.client=YouTubeClient(self.store,self.transport,clock=lambda:self.time,sleep=self.sleep)

    def tearDown(self):
        self.client.close();self.store.close();self.tmp.cleanup()

    def sleep(self, seconds): self.time+=seconds

    def transport(self,url):
        self.calls.append(url)
        return 200,{}, {'items':[{'id':'aaaaaaaaaaa','snippet':{'channelId':'UC'+'b'*22,'channelTitle':'Synthetic',
                                'title':'Synthetic geometry','publishedAt':'2020-01-01T00:00:00Z'}}],
                        **({} if 'pageToken=' in url else {'nextPageToken':'second'})}

    def test_likes_pagination_checkpoint_offline_rerun_and_not_watched(self):
        state=import_collection(self.store,self.client,likes=True,max_pages=1)
        self.assertFalse(state['complete']);self.assertEqual(len(self.calls),1)
        self.client.max_requests=1
        with self.assertRaises(BudgetExceeded):import_collection(self.store,self.client,likes=True,max_pages=1)
        self.assertEqual(self.store.get_checkpoint('creator_source:likes')['pages'],1)
        self.client.max_requests=2
        state=import_collection(self.store,self.client,likes=True,max_pages=1)
        self.assertTrue(state['complete'])
        self.client.offline=True
        import_collection(self.store,self.client,likes=True,max_pages=2)
        self.assertEqual(len(self.calls),2)
        self.assertEqual(self.store.db.execute('select count(*) from observations').fetchone()[0],1)
        self.assertEqual(self.store.db.execute('select kind,observed_at from observations').fetchone()[:],('liked',None))

    def test_unreviewed_negative_and_arbitrary_upload_playlists_are_rejected(self):
        with self.assertRaises(ValueError):import_collection(self.store,self.client,playlist_id='synthetic')
        with self.assertRaises(ValueError):self.client.get('playlistItems',{'playlistId':'UUunknown'})
        with self.assertRaises(ValueError):self.client.get('search',{'q':'synthetic'})
        self.assertEqual(len(self.calls),0)

    def test_metadata_caps_and_upload_sample_do_not_create_engagement(self):
        with self.store.db:
            self.store.checkpoint('creator_metadata', {'channels':{'UC'+'b'*22:{'item':{'contentDetails':{'relatedPlaylists':{'uploads':'UUknown'}}}}},'videos':{}})
        source=self.folder/'selection.json';source.write_text(json.dumps({'uploads':['UC'+'b'*22]}))
        report=inspect_metadata(self.store,self.client,source)
        self.assertIn('UC'+'b'*22,report['uploads'])
        self.assertEqual(self.store.db.execute('select count(*) from observations').fetchone()[0],0)
        source.write_text(json.dumps({'handles':['x']*16}))
        with self.assertRaises(ValueError):inspect_metadata(self.store,self.client,source)
        self.client.offline=True
        source.write_text(json.dumps({'uploads':['UC'+'b'*22]}))
        inspect_metadata(self.store,self.client,source)
        self.assertEqual(len(self.calls),1)
