"""Synthetic fixtures only: no personal catalog, account data or live network."""
from contextlib import closing
import hashlib
import errno
import http.client
import json
from pathlib import Path
import re
import tempfile
import threading
import unittest
from unittest.mock import patch

from pagefinder.arxiv_adapter import load_shelf, read_catalog, verified_local_ids
from pagefinder.learning import _cites_work, canonical_url, feedback, import_research, refresh, search, validate_research, work_id, works
from pagefinder.learning_server import make_learning_server
from pagefinder.local import main
from pagefinder.publication import check_text
from pagefinder.research import Store
from test_creators import batch


def event(root, name, time, **changes):
    (root / 'catalog').mkdir(exist_ok=True)
    (root / 'catalog' / name).write_text(json.dumps({'schema': 1, 'id': name, 'time': time, **changes}))


def paper(identifier='2301.00001v1', **extra):
    return {'arxiv_id': identifier, 'title': 'Synthetic vortex stability paper',
        'authors': ['Synthetic Author'], 'abstract': 'Synthetic numerical fluid stability and simulation test.',
        'published': '2023-01-01', 'filenames': ['private-filename.pdf'], **extra}


def assessed(url='https://example.org/synthetic-fluid', **extra):
    return {'url': url, 'title': 'Synthetic fluid simulation tutorial', 'kind': 'article',
        'authors': ['Synthetic Teacher'], 'summary': 'Numerical stability in a synthetic fluid simulation.',
        'learn': 'Compare a synthetic stable step and a residual.', 'topics': ['vortex validation'],
        'evidence_level': 'documentation_excerpt', 'verified_at': '2026-11-03T12:00:00+00:00',
        'duration_seconds': None, 'limitations': ['Synthetic fixture, not an actual recommendation.'],
        'evidence': [{'url': url, 'note': 'Synthetic documentation inspected.'}], **extra}


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_aliases_apply_before_all_metadata_and_rating_events_and_last_zero_clears(self):
        event(self.root, 'z.json', 1, papers={'old': {'filenames': ['one.pdf']}}, ratings={'old': 4})
        event(self.root, 'b.json', 2, papers={'new': paper()}, aliases={'old': 'new'})
        event(self.root, 'a.json', 3, papers={'new': {'filenames': ['two.pdf']}}, ratings={'old': 5})
        state, aliases, fingerprint = read_catalog(self.root)
        self.assertEqual(set(state), {'new'})
        self.assertEqual(state['new']['rating'], 5)
        self.assertEqual(state['new']['filenames'], ['one.pdf', 'private-filename.pdf', 'two.pdf'])
        event(self.root, 'clear.json', 4, ratings={'new': 0})
        rows, status = load_shelf(self.root)
        self.assertEqual(len(rows), 1); self.assertIsNone(rows[0]['star_rating'])
        self.assertEqual(rows[0]['arxiv_id'], '2301.00001v1')
        self.assertEqual(rows[0]['arxiv_version'], 1)
        self.assertEqual(rows[0]['arxiv_base'], '2301.00001')
        self.assertNotEqual(status['fingerprint'], fingerprint)
        self.assertNotIn('filenames', rows[0])

    def test_versions_are_preserved_and_multiple_filenames_do_not_duplicate_papers(self):
        event(self.root, 'a.json', 1, papers={'a': paper(), 'b': paper('2301.00001v2')})
        event(self.root, 'b.json', 2, papers={'a': {'filenames': ['another.pdf']}}, ratings={'b': 3})
        rows, status = load_shelf(self.root)
        self.assertEqual(len(rows), 2); self.assertEqual(status['rated'], 1)
        self.assertEqual({r['arxiv_version'] for r in rows}, {1, 2})

    def test_cache_is_not_catalog_and_only_contained_existing_pdf_headers_establish_presence(self):
        event(self.root, 'a.json', 1, papers={'a': paper(), 'b': paper('2301.00002')})
        cache = self.root / '.shelf'; cache.mkdir()
        downloads = self.root / 'downloads'; downloads.mkdir()
        valid = downloads / 'valid.pdf'; valid.write_bytes(b'%PDF-1.4 synthetic')
        outside = self.root / 'outside.pdf'; outside.write_bytes(b'%PDF-1.4 synthetic')
        (cache / 'index.json').write_text(json.dumps({'directory': str(downloads), 'papers': [
            {'arxiv_id': '2301.00002', 'path': str(downloads/'missing.pdf'), 'valid_pdf': True},
            {'arxiv_id': '2301.00001v1', 'path': str(valid), 'valid_pdf': True},
            {'arxiv_id': '2301.00002', 'path': str(outside), 'valid_pdf': True}]}))
        self.assertEqual(verified_local_ids(self.root), {'2301.00001v1'})
        (self.root / 'dist').mkdir(); (self.root / 'dist/catalog.json').write_text('{"stale":true}')
        before = {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        rows, _ = load_shelf(self.root)
        self.assertEqual(rows[0]['pdf_status'], 'verified_local')
        self.assertNotIn(str(self.root), json.dumps(rows))
        self.assertNotIn('private-filename', json.dumps(rows))
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_unresolved_rows_are_counted_without_inventing_source_urls(self):
        event(self.root, 'a.json', 1, papers={'a': {'title': 'Unknown identifier', 'filenames': ['x.pdf']}})
        rows, status = load_shelf(self.root)
        self.assertEqual(rows, []); self.assertEqual(status['unresolved'], 1)

    def test_corrupt_future_schema_and_invalid_ratings_fail_closed(self):
        event(self.root, 'a.json', 1, papers={'a': paper()}, ratings={'a': 8})
        with self.assertRaises(ValueError): read_catalog(self.root)
        (self.root/'catalog/a.json').write_text('{"schema":99}')
        with self.assertRaises(ValueError): read_catalog(self.root)


class LearningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.shelf = self.root / 'shelf'; self.shelf.mkdir()
        event(self.shelf, 'a.json', 1, papers={'a': paper()}, ratings={'a': 4})
        self.store = Store(self.root / 'data'); self.addCleanup(self.store.close)
        with self.store.db:
            self.store.checkpoint('learning_settings', {'arxiv_dir': str(self.shelf)})
        self.manifest = self.root / 'research.json'

    def research(self, rows):
        self.manifest.write_text(json.dumps({'version': 1, 'works': rows}))
        return import_research(self.store, self.manifest)

    def test_concept_citations_follow_actual_subproject_paths_and_do_not_bleed_into_siblings(self):
        cited = 'https://github.com/example/repo/blob/main/resonator/dsp.cc'
        self.assertTrue(_cites_work('https://github.com/example/repo/tree/main/resonator', cited))
        self.assertFalse(_cites_work('https://github.com/example/repo/tree/main/granular', cited))
        self.assertFalse(_cites_work('https://github.com/example/repo/tree/main/resonator', 'https://github.com/example/repo'))

    def test_idempotent_refresh_preserves_reviews_and_never_uses_network(self):
        with patch('urllib.request.urlopen', side_effect=AssertionError('No external requests')):
            refresh(self.store, self.shelf)
            row = works(self.store)[0]
            feedback(self.store, {'id': row['id'], 'action': 'useful', 'value': True, 'notes': 'Keep this'})
            before = tuple(self.store.db.execute('SELECT * FROM learning_feedback').fetchone())
            report = refresh(self.store)
        self.assertEqual(report['index']['changed'], 0)
        self.assertEqual(before, tuple(self.store.db.execute('SELECT * FROM learning_feedback').fetchone()))
        self.assertEqual(works(self.store)[0]['star_rating'], 4)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM reviews').fetchone()[0], 0)

    def test_missing_and_broken_shelf_retain_cached_items_and_good_refresh_deactivates_removed(self):
        refresh(self.store, self.shelf); row = works(self.store)[0]
        feedback(self.store, {'id': row['id'], 'action': 'saved', 'value': True})
        report = refresh(self.store, self.root/'absent')
        self.assertEqual(report['shelf']['status'], 'unavailable')
        self.assertEqual(len(works(self.store)), 1)
        (self.shelf/'catalog/a.json').write_text('{')
        self.assertEqual(refresh(self.store, self.shelf)['shelf']['status'], 'unavailable')
        (self.shelf/'catalog/a.json').unlink()
        self.assertEqual(refresh(self.store)['shelf']['papers'], 0)
        self.assertEqual(works(self.store), [])
        self.assertEqual(len(search(self.store, view='saved')['results']), 1)

    def test_curated_work_deduplicates_against_creators_and_does_not_change_creator_reviews(self):
        from pagefinder.creators import import_creator_batch
        source = self.root/'creators.json'; data = batch(); source.write_text(json.dumps(data))
        import_creator_batch(self.store, source)
        self.store.review('creator:synthetic', 'already_familiar', 'Original note')
        original = tuple(self.store.db.execute('SELECT * FROM reviews').fetchone())
        refresh(self.store, self.shelf)
        url = data['investigated'][0]['projects'][0]['url']
        self.research([assessed(url, kind='code')])
        matches = [w for w in works(self.store) if w['id'] == work_id(url)]
        self.assertEqual(len(matches), 1)
        self.assertIn('Earlier creator research', matches[0]['origins'])
        self.assertIn('Newly researched', matches[0]['origins'])
        self.assertEqual(tuple(self.store.db.execute('SELECT * FROM reviews').fetchone()), original)

    def test_earlier_project_source_excerpt_and_explicit_work_rejection_are_preserved(self):
        from pagefinder.creators import import_creator_batch
        source = self.root/'creators.json'; source.write_text(json.dumps(batch()))
        import_creator_batch(self.store, source)
        snapshot = self.root/'probe.json'
        snapshot.write_text(json.dumps({'connector_cache': {'responses': [
            {'kind': 'readme', 'repo': 'synthetic/project', 'result': {'structuredContent': {'content': 'Reversi search methods in a synthetic README.'}}}]}}))
        with self.store.db:
            ev = self.store.evidence('synthetic_probe', 'synthetic')
            self.store.entity('synthetic:project', 'github_repository', 'synthetic', 'Synthetic project', ev)
            self.store.checkpoint('active_candidate_batch', 'synthetic:probe')
            self.store.checkpoint('synthetic:probe', {'source_snapshot': str(snapshot), 'candidates': [{
                'repository_url': 'https://example.org/project', 'repository_full_name': 'synthetic/project',
                'entity_id': 'synthetic:project', 'why': 'Synthetic learning reason.',
                'readme_source': 'https://example.org/project/readme', 'readme_blob_sha': 'synthetic',
                'limitations': ['Synthetic fixture.']}]})
        refresh(self.store, self.shelf)
        row = search(self.store, 'Reversi search')['results'][0]
        self.assertIn('Earlier project research', row['origins'])
        self.store.review('synthetic:project', 'skip', 'Original explicit rejection')
        original = tuple(self.store.db.execute('SELECT * FROM reviews').fetchone())
        self.assertEqual(search(self.store, 'Reversi search')['results'], [])
        feedback(self.store, {'id': row['id'], 'action': 'useful', 'value': True})
        self.assertEqual(len(search(self.store, 'Reversi search')['results']), 1)
        self.assertEqual(tuple(self.store.db.execute('SELECT * FROM reviews').fetchone()), original)

    def test_feedback_dimensions_and_notes_survive_restart_without_implying_completion(self):
        refresh(self.store, self.shelf); row = works(self.store)[0]; key = row['id']
        for action in ('saved', 'useful'):
            feedback(self.store, {'id': key, 'action': action, 'value': True, 'notes': 'Durable'})
        self.assertFalse(works(self.store)[0]['feedback']['completed'])
        self.assertEqual(works(self.store)[0]['star_rating'], 4)
        feedback(self.store, {'id': key, 'action': 'completed', 'value': True})
        self.assertEqual(search(self.store, 'vortex')['results'], [])
        self.assertTrue(search(self.store, view='saved')['results'][0]['feedback']['completed'])
        with closing(Store(self.store.folder)) as reopened:
            state = works(reopened)[0]['feedback']; self.assertEqual(state['notes'], 'Durable')
            self.assertTrue(state['saved']); self.assertTrue(state['completed']); self.assertEqual(state['useful'], 1)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM reviews').fetchone()[0], 0)

    def test_dismissal_overrides_interest_and_remains_reversible_in_history(self):
        refresh(self.store, self.shelf); key = works(self.store)[0]['id']
        feedback(self.store, {'id': key, 'action': 'dismissed', 'value': True})
        self.assertEqual(search(self.store, 'vortex')['results'], [])
        self.assertEqual(len(search(self.store, view='dismissed')['results']), 1)
        feedback(self.store, {'id': key, 'action': 'dismissed', 'value': False})
        self.assertEqual(len(search(self.store, 'vortex')['results']), 1)

    def test_feedback_validation_precedes_writes_and_identical_save_preserves_timestamp(self):
        refresh(self.store, self.shelf); key = works(self.store)[0]['id']
        for data in ({'id': key, 'action': 'saved', 'value': 'yes'}, {'id': key, 'action': 'notes', 'notes': 'x'*4001}, {'id': 'unknown', 'action': 'saved', 'value': True}):
            with self.assertRaises(ValueError): feedback(self.store, data)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM learning_feedback').fetchone()[0], 0)
        data = {'id': key, 'action': 'saved', 'value': True}; feedback(self.store, data)
        original = tuple(self.store.db.execute('SELECT * FROM learning_feedback').fetchone())
        feedback(self.store, data)
        self.assertEqual(tuple(self.store.db.execute('SELECT * FROM learning_feedback').fetchone()), original)

    def test_query_specificity_rejects_generic_search_false_positives_and_parent_topic_pollution(self):
        self.research([assessed('https://example.org/higgs', title='Synthetic Higgs search', summary='Search physics experiments.', topics=[]),
            assessed('https://example.org/art', title='Synthetic image tool', summary='Drawing paths.', topics=[], creator_topics=['Reversi']),
            assessed('https://example.org/game', title='Synthetic game tree', summary='Bounded chess search.', topics=[], bridges=[
                {'label': 'Adversarial search', 'terms': ['reversi'], 'explanation': 'Synthetic transfer with different move rules.', 'sources': ['https://example.org/evidence']}])])
        result = search(self.store, 'Reversi search')['results']
        self.assertEqual([r['url'] for r in result], ['https://example.org/game'])
        self.assertEqual([r['url'] for r in search(self.store, 'Othello search')['results']], ['https://example.org/game'])
        self.assertEqual(result[0]['relation'], 'Method connection')
        self.assertEqual(search(self.store, 'purple elephant turbine')['results'], [])
        self.assertTrue(search(self.store, 'Please suggest a better fluid stability explanation')['results'])

    def test_formats_measured_duration_and_maximum_shortlist_do_not_invent_reading_times(self):
        rows = [assessed('https://example.org/'+str(i), kind='video' if i % 2 else 'article',
            duration_seconds=384 if i == 1 else None) for i in range(8)]
        self.research(rows)
        self.assertEqual(len(search(self.store, 'fluid simulation')['results']), 5)
        videos = search(self.store, 'fluid simulation', format='watch', time='short')['results']
        self.assertTrue(all(r['kind'] == 'video' for r in videos))
        self.assertIn('6 min 24 sec', videos[0]['effort'])
        self.assertTrue(any(r['effort'] == 'Duration unknown' for r in videos))
        self.assertTrue(all(r['kind'] in ('paper', 'article') for r in search(self.store, 'fluid simulation', format='read')['results']))
        for row in works(self.store):
            feedback(self.store, {'id': row['id'], 'action': 'saved', 'value': True})
        self.assertGreater(len(search(self.store, view='saved')['results']), 5)
        self.assertEqual(search(self.store, 'absentkeyword', view='saved')['results'], [])

    def test_versions_are_deduplicated_in_shortlist_but_not_source_index(self):
        event(self.shelf, 'b.json', 2, papers={'b': paper('2301.00001v2')})
        refresh(self.store, self.shelf)
        self.assertEqual(len(works(self.store)), 2)
        self.assertEqual(len(search(self.store, 'vortex stability')['results']), 1)

    def test_research_requires_scope_safe_evidence_and_same_work_chapter_url(self):
        for row in (assessed(evidence=[{'url': 'javascript:bad', 'note': 'bad'}]),
                    assessed(start_url='https://example.org/another'),
                    assessed(verified_at='2026-11-03'), assessed(verified_at=None),
                    assessed(evidence=[None]), assessed(topics='invalid'),
                    assessed(bridges=[None]), assessed(duration_seconds=-1)):
            with self.assertRaises(ValueError): validate_research({'version': 1, 'works': [row]})
        self.assertEqual(canonical_url('https://youtu.be/abcdefghijk?t=15'), 'https://www.youtube.com/watch?v=abcdefghijk')
        self.assertEqual(work_id('https://GitHub.com/OWNER/Repo'), work_id('https://github.com/owner/repo/'))

    def test_browser_payload_and_public_export_boundary_exclude_local_paths_and_collection_records(self):
        refresh(self.store, self.shelf)
        result = json.dumps(search(self.store, 'vortex stability'))
        self.assertNotIn(str(self.root), result); self.assertNotIn('private-filename.pdf', result)
        with self.assertRaises(ValueError): check_text(result)
        from pagefinder.core import ROOT
        before = {p: (ROOT/p).read_bytes() for p in ('data/sites.json', 'data/interests.json')}
        self.research([assessed()])
        self.assertEqual(before, {p: (ROOT/p).read_bytes() for p in before})
        for text in ('{"visibility":"private"}', '{"observed_at":"private"}'):
            with self.assertRaises(ValueError): check_text(text)

    def test_cli_refresh_accepts_missing_source_and_uses_only_private_outputs(self):
        self.assertEqual(main(['--data-dir', str(self.root/'other-data'), 'refresh-learning', '--arxiv-dir', str(self.root/'missing')]), 0)

    def test_learning_startup_port_diagnostic_is_actionable_and_hides_exception_details(self):
        import io
        from contextlib import redirect_stderr
        error = io.StringIO()
        with patch('pagefinder.learning_server.serve_learning', side_effect=OSError(errno.EADDRINUSE, 'PRIVATE_SERVER_DETAILS')), redirect_stderr(error):
            result = main(['--data-dir', str(self.root/'data'), 'serve-learning'])
        self.assertEqual(result, 2)
        self.assertIn('--port 8768', error.getvalue())
        self.assertIn('EADDRINUSE', error.getvalue())
        self.assertNotIn('PRIVATE_SERVER_DETAILS', error.getvalue())


class LearningHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.shelf = self.root/'shelf'; self.shelf.mkdir()
        event(self.shelf, 'a.json', 1, papers={'a': paper()})
        self.server = make_learning_server(self.root/'data', 0, self.shelf)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
        self.addCleanup(self.stop)
        self.origin = f'http://127.0.0.1:{self.server.server_port}'
        self.connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        self.addCleanup(self.connection.close)

    def stop(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()

    def get(self, path):
        self.connection.request('GET', path); r = self.connection.getresponse(); return r.status, r.read(), r

    def post(self, path, data, origin=None, token=''):
        self.connection.request('POST', path, json.dumps(data), {'Content-Type': 'application/json',
            'Origin': self.origin if origin is None else origin, 'X-Review-Token': token})
        r = self.connection.getresponse(); return r.status, r.read()

    def test_loopback_routes_and_origin_token_checks_and_durable_feedback(self):
        code, body, response = self.get('/'); self.assertEqual(code, 200)
        self.assertIn(b'What would you like to learn', body)
        self.assertEqual(response.getheader('Cache-Control'), 'no-store')
        token = re.search(rb'const TOKEN="([^"]+)"', body)[1].decode()
        code, data, _ = self.get('/api/search?q=vortex'); self.assertEqual(code, 200)
        result = json.loads(data)['results'][0]
        update = {'id': result['id'], 'action': 'saved', 'value': True, 'notes': 'Synthetic durable note'}
        self.assertEqual(self.post('/api/learning-feedback', update, token=token, origin='https://evil.example')[0], 403)
        self.assertEqual(self.post('/api/learning-feedback', update, token='bad')[0], 403)
        self.assertEqual(self.post('/api/learning-feedback', update, token='é')[0], 403)
        self.assertEqual(self.post('/api/learning-feedback', update, token=token)[0], 200)
        saved = json.loads(self.get('/api/search?view=saved')[1])['results'][0]
        self.assertEqual(saved['feedback']['notes'], 'Synthetic durable note')
        self.assertFalse(saved['feedback']['completed'])
        self.assertEqual(self.get('/research.sqlite3')[0], 404)
        self.assertEqual(self.get('/../catalog')[0], 404)
        self.assertEqual(self.get('/api/search?q=a&q=b')[0], 400)
        self.assertEqual(self.get('/api/search?format=invalid')[0], 400)
        self.assertNotIn(str(self.root), json.dumps(saved))
        self.assertEqual(self.post('/api/refresh', {}, token=token)[0], 200)

    def test_host_binding_rejects_localhost_alias_and_startup_validates_port(self):
        self.connection.request('GET', '/', headers={'Host': 'evil.example'})
        response = self.connection.getresponse(); self.assertEqual(response.status, 403); response.read()
        with self.assertRaisesRegex(ValueError, 'Port'):
            make_learning_server(self.root/'data', 70000, self.shelf)

    def test_storage_failure_is_sanitized_and_the_next_request_can_recover(self):
        with patch('pagefinder.learning_server.Store', side_effect=OSError('PRIVATE_STORAGE_DETAILS')):
            code, body, _ = self.get('/api/status')
        self.assertEqual(code, 503)
        self.assertIn(b'Private storage is unavailable', body)
        self.assertNotIn(b'PRIVATE_STORAGE_DETAILS', body)
        self.assertEqual(self.get('/api/status')[0], 200)
