from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pagefinder.core import ROOT
from pagefinder.interests import (DEFAULT_SEEDS, DEFAULT_SOURCE, import_bookshelf, score_private,
                                  set_interest_scope, write_interest_graph)
from pagefinder.local import main
from pagefinder.research import Store


class BookshelfTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.store = Store(self.folder / 'private')

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_titles_provenance_typed_links_and_unknown_priorities(self):
        with patch('socket.create_connection', side_effect=AssertionError('No network allowed')):
            report = import_bookshelf(self.store)
        self.assertEqual(len(report['books']), 13)
        self.assertEqual(len(report['hypotheses']), 6)
        self.assertEqual(report['evidence_type'], 'physical_book_visible')
        self.assertFalse(report['preference_weights_assigned'])
        self.assertEqual(report['independent_photograph_sources'], 1)
        for book in report['books']:
            self.assertEqual(book['reading_status'], 'unspecified')
            self.assertEqual(book['discovery_priority'], 'unspecified')
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM observations').fetchone()[0], 0)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM entities WHERE published_at IS NOT NULL').fetchone()[0], 0)
        evidence = self.store.db.execute("SELECT notes FROM evidence WHERE source_type='bookshelf_photo_2026_11_02'").fetchone()
        self.assertEqual(json.loads(evidence[0])['evidence_type'], 'physical_book_visible')
        statuses = {r['status'] for r in report['relationships']}
        self.assertEqual(statuses, {'known', 'inferred', 'hypothesis'})
        for edge in report['relationships']:
            self.assertTrue(edge['falsification'])
            self.assertIsNotNone(self.store.db.execute('SELECT 1 FROM evidence WHERE id=?', (edge['evidence_id'],)).fetchone())
            if edge['predicate'] in ('covers_subject', 'uses_method', 'has_historical_context'):
                self.assertEqual(edge['status'], 'inferred')
        self.assertEqual(self.store.db.execute('PRAGMA user_version').fetchone()[0], 1)

    def test_rerun_reuses_snapshot_and_graph_without_inflating_support(self):
        first = import_bookshelf(self.store)
        counts = self.store.coverage()['counts']
        second = import_bookshelf(self.store)
        self.assertEqual(counts, self.store.coverage()['counts'])
        self.assertEqual(first['snapshot_sha256'], second['snapshot_sha256'])
        self.assertEqual(len(list((self.store.folder / 'sources').glob('bookshelf-*.json'))), 1)
        self.assertEqual(len({e['id'] for e in second['relationships']}), len(second['relationships']))

    def test_low_aggregate_completion_is_private_and_does_not_assign_book_progress(self):
        report = import_bookshelf(self.store, overall_reading_completion='low')
        self.assertEqual(report['reading_completion_feedback']['overall'], 'low')
        self.assertEqual(report['reading_completion_feedback']['per_book'], 'unspecified')
        self.assertTrue(all(b['reading_status'] == 'unspecified' for b in report['books']))
        self.assertTrue(all(b['discovery_priority'] == 'unspecified' for b in report['books']))
        self.assertTrue(all(q['eligible_for_exploration'] for q in report['hypotheses']))
        evidence = self.store.db.execute("SELECT visibility,notes FROM evidence WHERE source_type='manual_bookshelf_feedback'").fetchone()
        self.assertEqual(evidence['visibility'], 'private')
        self.assertEqual(json.loads(evidence['notes'])['interest_strength_change'], 'none')
        self.assertEqual(import_bookshelf(self.store)['reading_completion_feedback']['overall'], 'low')

    def test_explicit_reviews_survive_import_and_override_hypothesis_eligibility(self):
        report = import_bookshelf(self.store)
        book, question = report['books'][0]['entity_id'], report['hypotheses'][0]['entity_id']
        self.store.review(book, 'keep', 'Synthetic current reference')
        self.store.review(question, 'skip', 'Synthetic irrelevant connection')
        report = import_bookshelf(self.store)
        self.assertEqual(report['books'][0]['review']['decision'], 'keep')
        self.assertFalse(report['hypotheses'][0]['eligible_for_exploration'])
        self.assertEqual(report['hypotheses'][0]['review']['reason'], 'Synthetic irrelevant connection')

    def test_changed_title_or_invalid_topic_map_is_not_silently_guessed(self):
        source = self.folder / 'source.md'
        source.write_text(DEFAULT_SOURCE.read_text().replace('*Essentials of Robust Control*', '*Different book*'))
        with self.assertRaises(ValueError):
            import_bookshelf(self.store, source)
        seeds = self.folder / 'seeds.json'
        spec = json.loads(DEFAULT_SEEDS.read_text())
        spec['books'][0]['concepts'] = ['unknown_concept']
        seeds.write_text(json.dumps(spec))
        with self.assertRaises(ValueError):
            import_bookshelf(self.store, seeds=seeds)
        self.assertEqual(self.store.coverage()['counts']['entities'], 0)
        self.assertFalse((self.store.folder / 'sources').exists())

    def test_hypotheses_are_bounded_and_primary_references_are_not_preference_claims(self):
        report = import_bookshelf(self.store)
        self.assertEqual(report['expansion_depth'], 1)
        self.assertLessEqual(len(report['hypotheses']), report['hypothesis_limit'])
        for question in report['hypotheses']:
            self.assertTrue(question['reference']['url'].startswith('https://'))
            self.assertTrue(question['entry_point'])
            self.assertTrue(question['falsification'])
        spec = json.loads(DEFAULT_SEEDS.read_text())
        spec['hypotheses'] = [dict(spec['hypotheses'][0], id=str(i)) for i in range(11)]
        seeds = self.folder / 'seeds.json'
        seeds.write_text(json.dumps(spec))
        with self.assertRaises(ValueError):
            import_bookshelf(self.store, seeds=seeds)

    def test_private_artifacts_public_baseline_and_existing_engagement_are_preserved(self):
        paths = [ROOT / 'data/interests.json', ROOT / 'data/sites.json', ROOT / 'docs/index.html', DEFAULT_SOURCE]
        before = {p: p.read_bytes() for p in paths}
        with self.store.db:
            evidence = self.store.evidence('synthetic_other_source', 'synthetic')
            self.store.entity('synthetic:video', 'youtube_video', 'synthetic', 'Synthetic', evidence)
            self.store.observe('synthetic:event', 'synthetic:video', 'history_seen', None, evidence)
        import_bookshelf(self.store)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM observations').fetchone()[0], 1)
        for p in paths:
            self.assertEqual(before[p], p.read_bytes())
        for name in ('interest_graph.json', 'interest_graph.html', 'evidence_coverage.json'):
            self.assertEqual((self.store.folder / name).stat().st_mode & 0o777, 0o600)
        page = (self.store.folder / 'interest_graph.html').read_text()
        self.assertIn("connect-src 'none'", page)
        self.assertIn('Hypothesis:', page)

    def test_cli_import_and_graph_refresh_do_not_need_credentials(self):
        out = io.StringIO()
        base = ['--data-dir', str(self.store.folder)]
        with redirect_stdout(out):
            self.assertEqual(main(base + ['import-bookshelf', '--overall-reading-completion', 'low']), 0)
            self.assertEqual(main(base + ['review', 'question:bookshelf:formal_algebra', 'skip', '--reason', 'Synthetic feedback']), 0)
            self.assertEqual(main(base + ['interest-graph']), 0)
        self.assertIn('13 volumes', out.getvalue())
        report = write_interest_graph(self.store)
        target = next(h for h in report['hypotheses'] if h['id'] == 'formal_algebra')
        self.assertFalse(target['eligible_for_exploration'])

    def test_explicit_application_scope_overrides_weak_topic_links_and_keyword_contributions(self):
        baseline_path = ROOT / 'data/interests.json'
        original = baseline_path.read_bytes()
        import_bookshelf(self.store, overall_reading_completion='low')
        topic = 'Fluid dynamics and Navier–Stokes'
        report = set_interest_scope(self.store, topic, 'Synthetic pump applications', ['pump'],
                                    project_status='stopped', note='Synthetic context-only correction')
        fluid_questions = [h for h in report['hypotheses'] if topic in h['baseline_topics']]
        self.assertEqual(len(fluid_questions), 2)
        self.assertTrue(all(not h['eligible_for_exploration'] for h in fluid_questions))
        self.assertTrue(all(h['context_requirements'] for h in fluid_questions))
        profile = report['effective_keyword_profile']
        restricted = next(t for t in profile['interests'] if t.get('baseline_topic') == topic)
        self.assertEqual(restricted['name'], 'Synthetic pump applications')
        minimal = {'interests': [restricted]}
        self.assertEqual(score_private({'title': 'Navier-Stokes and vortex dynamics'}, minimal)['score'], 0)
        self.assertGreater(score_private({'title': 'Pump Navier-Stokes and vortex dynamics'}, minimal)['score'], 0)
        self.assertEqual(baseline_path.read_bytes(), original)
        evidence = self.store.db.execute("SELECT visibility FROM evidence WHERE source_type='manual_interest_scope'").fetchone()
        self.assertEqual(evidence[0], 'private')
        self.assertTrue(any(e['predicate'] == 'requires_context' and e['status'] == 'known'
                            for e in report['relationships']))
        rerun = import_bookshelf(self.store)
        self.assertEqual(rerun['interest_scope_corrections'][0]['related_project_status'], 'stopped')
        self.assertEqual(rerun['reading_completion_feedback']['overall'], 'low')
        self.assertTrue(all(b['discovery_priority'] == 'unspecified' for b in rerun['books']))

    def test_scope_cli_is_idempotent_and_rejects_unknown_topics(self):
        import_bookshelf(self.store)
        args = ['--data-dir', str(self.store.folder), 'set-interest-scope',
                'Fluid dynamics and Navier–Stokes', '--label', 'Synthetic applications',
                '--context', 'pump', '--project-status', 'stopped', '--note', 'Synthetic correction']
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(args), 0)
            counts = self.store.coverage()['counts']
            self.assertEqual(main(args), 0)
            self.assertEqual(counts, self.store.coverage()['counts'])
        with self.assertRaises(ValueError):
            set_interest_scope(self.store, 'Unknown topic', 'Synthetic', ['pump'])

    def test_soft_preference_retains_general_exploration_and_respects_explicit_skips(self):
        import_bookshelf(self.store)
        topic = 'Fluid dynamics and Navier–Stokes'
        report = set_interest_scope(self.store, topic, 'Synthetic preferred application', ['pump'], mode='prefer')
        questions = [q for q in report['hypotheses'] if topic in q['baseline_topics']]
        self.assertTrue(all(q['eligible_for_exploration'] for q in questions))
        self.assertTrue(all(q['scope_status'].startswith('exploratory_until') for q in questions))
        profile = {'interests': [next(t for t in report['effective_keyword_profile']['interests']
                                     if t.get('baseline_topic') == topic)]}
        general = score_private({'title': 'Navier-Stokes vortex dynamics'}, profile)
        preferred = score_private({'title': 'Pump Navier-Stokes vortex dynamics'}, profile)
        self.assertEqual(general['primary_points'], 0)
        self.assertGreater(general['exploratory_points'], 0)
        self.assertGreater(preferred['primary_points'], 0)
        self.assertFalse(preferred['exploratory_topics'])
        self.store.review(questions[0]['entity_id'], 'skip', 'Synthetic explicit skip')
        updated = write_interest_graph(self.store)
        self.assertFalse(next(q for q in updated['hypotheses'] if q['entity_id'] == questions[0]['entity_id'])['eligible_for_exploration'])


if __name__ == '__main__':
    unittest.main()
