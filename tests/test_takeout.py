import json
from pathlib import Path
import shutil
import tempfile
import unittest

from pagefinder.research import Store
from pagefinder.takeout import import_takeout, timestamp, video_id

FIXTURES = Path(__file__).parent / 'fixtures/takeout-v1'


class TakeoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.store = Store(self.folder / 'private')

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def source(self, name):
        dest = self.folder / name
        shutil.copyfile(FIXTURES / name, dest)
        return dest

    def test_history_repeat_events_timezones_missing_ids_and_idempotent_import(self):
        path = self.source('history.json')
        first = import_takeout(self.store, path, 'history')
        self.assertEqual(first['rows'], 6)
        self.assertEqual(first['imported_observations'], 4)
        self.assertEqual(first['unavailable_or_unrecognized'], 2)
        self.assertEqual(first['missing_or_ambiguous_time'], 1)
        repeated = self.store.db.execute("SELECT observed_at FROM observations WHERE entity_id='youtube:video:aaaaaaaaaaa'").fetchall()
        self.assertEqual(len(repeated), 2)
        self.assertEqual(repeated[0][0], repeated[1][0])
        second = import_takeout(self.store, path, 'history')
        self.assertEqual(second['imported_observations'], 0)
        self.assertEqual(second['duplicates'], 4)
        self.assertEqual(first['watch_minutes'], 'not_measurable')
        self.assertTrue(Path(first['source_snapshot']).exists())
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM entities WHERE kind="youtube_channel"').fetchone()[0], 1)

    def test_json_and_html_exports_reconcile_the_same_event(self):
        import_takeout(self.store, self.source('history.json'), 'history')
        report = import_takeout(self.store, self.source('watch-history.html'), 'history')
        self.assertEqual(report['duplicates'], 1)
        self.assertEqual(report['unavailable_or_unrecognized'], 1)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM observations').fetchone()[0], 4)

    def test_likes_and_watch_later_do_not_create_watch_events(self):
        likes = import_takeout(self.store, self.source('likes.csv'), 'likes')
        later = import_takeout(self.store, self.source('watch-later.csv'), 'watch_later')
        self.assertEqual(likes['imported_observations'], 2)
        self.assertEqual(later['imported_observations'], 2)
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM observations WHERE kind='history_seen'").fetchone()[0], 0)
        kinds = {r[0] for r in self.store.db.execute('SELECT kind FROM observations')}
        self.assertEqual(kinds, {'liked', 'watch_later'})

    def test_curation_import_requires_prior_playlist_review(self):
        with self.assertRaises(ValueError):
            import_takeout(self.store, self.source('likes.csv'), 'playlist', playlist_id='synthetic')

    def test_malformed_json_is_snapshotted_but_not_imported(self):
        path = self.folder / 'malformed.json'
        path.write_text('{"unexpected":"format"}')
        with self.assertRaises(ValueError):
            import_takeout(self.store, path, 'history')
        self.assertEqual(self.store.coverage()['counts']['observations'], 0)
        self.assertEqual(len(list((self.store.folder / 'sources').glob('*.json'))), 1)

    def test_dates_and_urls_are_not_guessed(self):
        self.assertEqual(timestamp('2024-03-01T23:30:00-05:00'), '2024-03-02T04:30:00+00:00')
        self.assertIsNone(timestamp('03/04/24 12:00'))
        self.assertIsNone(timestamp('Mar 2, 2024, 4:30:00 AM CST'))
        self.assertIsNone(video_id('https://youtube.com.evil.test/watch?v=aaaaaaaaaaa'))
        self.assertEqual(video_id('https://youtu.be/aaaaaaaaaaa'), 'aaaaaaaaaaa')


if __name__ == '__main__':
    unittest.main()
