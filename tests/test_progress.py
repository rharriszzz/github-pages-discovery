from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from pagefinder.candidates import import_candidate_batch, write_review_queue
from pagefinder.core import ROOT
from pagefinder.interests import import_bookshelf, import_interest_notes, score_private, write_interest_graph
from pagefinder.local import main
from pagefinder.research import Store


class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.store = Store(self.folder / 'private')
        self.notes = self.folder / 'notes.json'
        self.notes.write_text(json.dumps({'version': 1,
            'background': [{'label': 'Synthetic prior training', 'note': 'User reported; not a proficiency inference'}],
            'interests': [{'label': 'Synthetic explicit interest', 'kind': 'subject', 'terms': ['synthetic lattice']}],
            'resources': [{'label': 'Synthetic liked resource', 'url': 'https://example.test/resource', 'note': 'No reading-completion claim'}],
            'hypotheses': [{'label': 'Synthetic proposed connection', 'note': 'Not an explicit preference'}]}))
        import_bookshelf(self.store)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def batch(self):
        repo = 'synthetic/example'
        meta = {'id': 1234, 'full_name': repo, 'private': False, 'owner': {'id': 9, 'login': 'synthetic', 'type': 'User'},
                'html_url': 'https://github.com/' + repo, 'archived': False, 'pushed_at': '2025-01-01T00:00:00Z',
                'description': 'A synthetic lattice tool', 'topics': ['synthetic-lattice']}
        cache = {'logical_connector_calls': 3, 'responses': [
            {'kind': 'metadata', 'repo': repo, 'result': {'structuredContent': {'content': json.dumps(meta)}}},
            {'kind': 'readme', 'repo': repo, 'result': {'isError': True}},
            {'kind': 'readme', 'repo': repo, 'result': {'structuredContent': {'sha': 'synthetic-sha',
                'content': 'Synthetic lattice example', 'display_url': 'https://github.com/' + repo + '/blob/main/README.md'}}}]}
        (self.folder / 'connector.json').write_text(json.dumps(cache))
        (self.folder / 'sites.json').write_text(json.dumps({'site_fetch_reservations': 2,
            'results': [{'url': 'https://synthetic.github.io/', 'site_status': 'ok'}]}))
        source = self.folder / 'batch.json'
        source.write_text(json.dumps({'version': 1, 'connector_cache': 'connector.json', 'site_checks': 'sites.json',
            'limitations': ['Synthetic targeted sample; usefulness unknown'], 'candidates': [{
                'repository_full_name': repo, 'site_url': 'https://synthetic.github.io/',
                'why': 'Synthetic research connection', 'facets': {'direct_fit': 'possible'},
                'limitations': ['Synthetic software not executed']}]}))
        return source

    def test_explicit_notes_keep_background_appreciation_and_proposals_distinct(self):
        public = (ROOT / 'data/interests.json').read_bytes()
        import_interest_notes(self.store, self.notes)
        graph = write_interest_graph(self.store)
        self.assertEqual(len(graph['books']), 13)  # Appreciated resource is not a newly photographed book.
        self.assertEqual(graph['explicit_statements']['interests'][0]['status'], 'user_reported')
        self.assertEqual(graph['explicit_statements']['hypotheses'][0]['status'], 'hypothesis')
        self.assertTrue(all(b['reading_status'] == 'unspecified' for b in graph['books']))
        result = score_private({'title': 'A synthetic lattice implementation'}, graph['effective_keyword_profile'])
        self.assertEqual(result['declared_matches'][0]['topic'], 'Synthetic explicit interest')
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM observations').fetchone()[0], 0)
        self.assertEqual((ROOT / 'data/interests.json').read_bytes(), public)

    def test_note_import_is_idempotent_and_preserves_other_private_feedback(self):
        first = import_interest_notes(self.store, self.notes)
        counts = self.store.coverage()['counts']
        nid = next(iter(first['interests']))
        self.store.review(nid, 'keep', 'Synthetic review')
        import_interest_notes(self.store, self.notes)
        self.assertEqual(self.store.coverage()['counts']['concepts'], counts['concepts'])
        self.assertEqual(self.store.db.execute('SELECT decision FROM reviews WHERE entity_id=?', (nid,)).fetchone()[0], 'keep')
        self.assertEqual((self.store.folder / 'explicit_interest_notes.json').stat().st_mode & 0o777, 0o600)
        self.assertFalse(any(r[0] != 'private' for r in self.store.db.execute(
            "SELECT visibility FROM evidence WHERE source_type='manual_interest_notes'")))

    def test_private_note_cli_and_invalid_resource_fail_closed(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(['--data-dir', str(self.store.folder), 'import-interest-notes', str(self.notes)]), 0)
        payload = json.loads(self.notes.read_text())
        payload['resources'][0]['url'] = 'javascript:alert(1)'
        self.notes.write_text(json.dumps(payload))
        with self.assertRaises(ValueError):
            import_interest_notes(self.store, self.notes)

    def test_candidate_queue_uses_cached_evidence_and_separate_comparison_facets(self):
        import_interest_notes(self.store, self.notes)
        report = import_candidate_batch(self.store, self.batch())
        self.assertEqual(len(report['candidates']), 1)
        item = report['candidates'][0]
        self.assertEqual(item['owner_type'], 'User')
        self.assertEqual(item['site_check'], 'ok')
        self.assertEqual(item['novelty'], 'user_familiarity_unknown')
        self.assertTrue(item['comparison']['private_facets']['declared_matches'])
        self.assertFalse(report['all_candidates_human_evaluated'])
        self.assertEqual(report['failed_connector_calls'], 1)
        self.assertEqual((self.store.folder / 'discovery_queue.html').stat().st_mode & 0o777, 0o600)
        self.assertIn('Baseline keyword score: 0', (self.store.folder / 'discovery_queue.html').read_text())

    def test_candidate_rerun_preserves_reviews_and_does_not_duplicate_candidates(self):
        report = import_candidate_batch(self.store, self.batch())
        eid = report['candidates'][0]['entity_id']
        self.store.review(eid, 'later', 'Synthetic queue feedback')
        import_candidate_batch(self.store, self.folder / 'batch.json')
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM candidates').fetchone()[0], 1)
        self.assertEqual(write_review_queue(self.store)['candidates'][0]['review']['decision'], 'later')

    def test_candidate_batch_rejects_missing_evidence_and_path_escape(self):
        source = self.batch()
        data = json.loads(source.read_text())
        data['candidates'][0]['repository_full_name'] = 'unknown/missing'
        source.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            import_candidate_batch(self.store, source)
        data['connector_cache'] = '../escape.json'
        source.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            import_candidate_batch(self.store, source)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM candidates').fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
