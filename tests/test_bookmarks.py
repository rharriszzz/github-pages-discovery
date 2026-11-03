from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from pagefinder.bookmarks import canonical_url, chrome_time, import_bookmarks
from pagefinder.core import ROOT
from pagefinder.local import main
from pagefinder.research import Store

FIXTURE = Path(__file__).parent / 'fixtures/chrome-v1/bookmarks.json'


class BookmarkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.source = self.folder / 'Bookmarks'
        shutil.copyfile(FIXTURE, self.source)
        self.store = Store(self.folder / 'private')

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def rewrite(self, edit):
        document = json.loads(self.source.read_text())
        edit(document)
        self.source.write_text(json.dumps(document))

    def test_selected_folders_nested_paths_deduplication_and_signal_semantics(self):
        original = self.source.read_bytes()
        with patch('socket.create_connection', side_effect=AssertionError('No network allowed')):
            report = import_bookmarks(self.store, self.source, ['study', 'TOOLS'])
        self.assertEqual(report['bookmark_nodes'], 8)
        self.assertEqual(report['unique_items'], 4)
        self.assertEqual(report['saved_memberships'], 5)
        self.assertEqual(report['new_saved_memberships'], 5)
        self.assertEqual(report['excluded'], 2)
        self.assertEqual(report['missing_or_invalid_added_dates'], 2)
        self.assertIn(['bookmark_bar', 'Study', 'Methods'], [r['folder_path'] for r in report['bookmarks']])
        self.assertEqual({r[0] for r in self.store.db.execute('SELECT kind FROM observations')}, {'saved'})
        self.assertEqual({r[0] for r in self.store.db.execute('SELECT visibility FROM entities')}, {'private'})
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM entities WHERE published_at IS NOT NULL').fetchone()[0], 0)
        self.assertEqual(report['external_requests'], 0)
        self.assertEqual(self.source.read_bytes(), original)

    def test_rerun_is_idempotent_preserves_reviews_and_reuses_subset_snapshot(self):
        first = import_bookmarks(self.store, self.source, ['Study', 'Tools'])
        entity = first['bookmarks'][0]['entity_id']
        self.store.review(entity, 'keep', 'Synthetic explicit feedback')
        second = import_bookmarks(self.store, self.source, ['Study', 'Tools'])
        self.assertEqual(second['new_saved_memberships'], 0)
        self.assertEqual(second['existing_or_duplicate_memberships'], 6)
        self.assertEqual(first['source_sha256'], second['source_sha256'])
        self.assertEqual(len(list((self.store.folder / 'sources').glob('*.json'))), 1)
        self.assertEqual(self.store.db.execute('SELECT decision FROM reviews').fetchone()[0], 'keep')
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM observations').fetchone()[0], 5)

    def test_unselected_records_sync_metadata_and_last_used_never_persist(self):
        report = import_bookmarks(self.store, self.source, ['Study', 'Tools'])
        for path in self.store.folder.rglob('*'):
            if path.is_file():
                self.assertNotIn(b'DO_NOT_PERSIST', path.read_bytes(), str(path))
                self.assertNotIn(b'unselected.invalid', path.read_bytes(), str(path))
        self.assertEqual(Path(report['source_snapshot']).stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.store.folder / 'bookmark_inventory.html').stat().st_mode & 0o777, 0o600)

    def test_ambiguous_missing_overlapping_or_empty_selection_has_no_side_effects(self):
        for selectors in ([], ['missing'], ['Methods', 'Study'], ['Study', 'study']):
            with self.assertRaises(ValueError):
                import_bookmarks(self.store, self.source, selectors)
        self.rewrite(lambda d: d['roots']['bookmark_bar']['children'].append(
            {'type': 'folder', 'name': 'Study', 'guid': 'second-study', 'children': []}))
        with self.assertRaises(ValueError):
            import_bookmarks(self.store, self.source, ['Study'])
        self.assertEqual(self.store.coverage()['counts']['observations'], 0)
        self.assertFalse((self.store.folder / 'sources').exists())
        # A full path disambiguates same-name folders in different parents.
        self.rewrite(lambda d: d['roots']['bookmark_bar']['children'].__setitem__(-1,
            {'type': 'folder', 'name': 'Other', 'guid': 'other', 'children': [
                {'type': 'folder', 'name': 'Study', 'guid': 'second-study', 'children': []}]}))
        report = import_bookmarks(self.store, self.source, ['bookmark_bar/Study'])
        self.assertEqual(report['bookmark_nodes'], 6)

    def test_shared_youtube_id_matches_existing_takeout_entity(self):
        with self.store.db:
            evidence = self.store.evidence('synthetic_history', 'synthetic')
            self.store.entity('youtube:video:aaaaaaaaaaa', 'youtube_video', 'aaaaaaaaaaa', 'Earlier title', evidence)
        import_bookmarks(self.store, self.source, ['Study'])
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM entities WHERE kind='youtube_video'").fetchone()[0], 1)
        self.assertIsNotNone(self.store.db.execute("SELECT * FROM observations WHERE entity_id='youtube:video:aaaaaaaaaaa'").fetchone())

    def test_dates_urls_html_escaping_and_publication_isolation(self):
        self.assertEqual(chrome_time('13348540800000000'), '2024-01-01T00:00:00+00:00')
        for value in ('0', '-1', 'bad', '99999999999999999999', 13348540800000000):
            self.assertIsNone(chrome_time(value))
        self.assertEqual(canonical_url('https://EXAMPLE.test:443/lesson?q=1#part'),
                         'https://example.test/lesson?q=1#part')
        for url in ('javascript:alert(1)', 'file:///tmp/bookmark', 'https://u:p@example.test/',
                    'https://example.test:bad/', 'https://example.test/a\nb'):
            self.assertIsNone(canonical_url(url))
        public = ROOT / 'docs/index.html'
        original = public.read_bytes()
        import_bookmarks(self.store, self.source, ['Study', 'Tools'])
        page = (self.store.folder / 'bookmark_inventory.html').read_text()
        self.assertIn('&lt;script&gt;synthetic()', page)
        self.assertNotIn('<script>synthetic()', page)
        self.assertNotIn('javascript:alert', page)
        self.assertIn("connect-src 'none'", page)
        self.assertEqual(public.read_bytes(), original)

    def test_changed_selection_retains_prior_evidence_and_source_snapshots(self):
        first = import_bookmarks(self.store, self.source, ['Tools'])
        self.rewrite(lambda d: d['roots']['bookmark_bar']['children'][1]['children'][0].update(
            name='Updated synthetic title'))
        second = import_bookmarks(self.store, self.source, ['Tools'])
        self.assertNotEqual(first['source_sha256'], second['source_sha256'])
        self.assertEqual(second['new_saved_memberships'], 0)
        self.assertEqual(len(list((self.store.folder / 'sources').glob('*.json'))), 2)
        self.assertIn('Shared course', {r[0] for r in self.store.db.execute('SELECT title FROM titles')})

    def test_malformed_source_and_in_repo_source_are_rejected_safely(self):
        for text in ('{bad', '{"version":2,"roots":{}}', '{"version":1,"roots":[]}'):
            self.source.write_text(text)
            with self.assertRaises(ValueError):
                import_bookmarks(self.store, self.source, ['Study'])
        with self.assertRaises(ValueError):
            import_bookmarks(self.store, FIXTURE, ['Study'])
        self.assertEqual(self.store.coverage()['counts']['observations'], 0)

    def test_cli_reports_counts_without_printing_titles_or_urls(self):
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(output):
            result = main(['--data-dir', str(self.store.folder), 'import-bookmarks', str(self.source),
                           '--folder', 'Study', '--folder', 'Tools'])
        self.assertEqual(result, 0)
        self.assertIn('8 entries', output.getvalue())
        self.assertNotIn('Synthetic course', output.getvalue())
        self.assertNotIn('https://example.test', output.getvalue())


if __name__ == '__main__':
    unittest.main()
