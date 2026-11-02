import json
from pathlib import Path
import tempfile
import unittest

from pagefinder.net import BudgetExceeded, ResponseError
from pagefinder.research import Store
from pagefinder.youtube import YouTubeClient, annotate, inventory, inventory_rows

FIXTURES = Path(__file__).parent / 'fixtures/youtube-v1'


class PlaylistTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / 'private')
        self.time = 1700000000.0
        self.calls = []
        self.client = self.make_client()

    def tearDown(self):
        self.client.close()
        self.store.close()
        self.tmp.cleanup()

    def sleep(self, duration):
        self.time += duration

    def transport(self, url):
        self.calls.append(url)
        name = 'playlists-2.json' if 'pageToken=' in url else 'playlists-1.json'
        return 200, {'ETag': name}, json.loads((FIXTURES / name).read_text())

    def make_client(self, **options):
        return YouTubeClient(self.store, self.transport, clock=lambda: self.time, sleep=self.sleep, **options)

    def test_inventory_paginates_deduplicates_and_never_downloads_videos(self):
        state = inventory(self.store, self.client)
        self.assertTrue(state['complete'])
        self.assertEqual(len(inventory_rows(self.store)), 3)
        self.assertEqual({r['privacy'] for r in inventory_rows(self.store)}, {'private', 'unlisted', 'public'})
        self.assertEqual(len(self.calls), 2)
        self.assertTrue(all('/playlists?' in u and 'mine=true' in u and 'maxResults=50' in u for u in self.calls))
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM observations').fetchone()[0], 0)
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM titles WHERE entity_id='youtube:playlist:PLsynthetic1'").fetchone()[0], 2)
        with self.assertRaises(ValueError):
            self.client.get('playlistItems', {'playlistId': 'synthetic'})

    def test_page_checkpoint_resume_offline_rerun_and_annotation_preservation(self):
        first = inventory(self.store, self.client, max_pages=1)
        self.assertFalse(first['complete'])
        inventory(self.store, self.client)
        path = Path(self.tmp.name) / 'annotations.json'
        path.write_text(json.dumps({'version': 1, 'playlists': [
            {'id': 'PLsynthetic1', 'purpose': 'favorites', 'relevance': 'positive',
             'notes': 'Synthetic note', 'reviewed': True}]}))
        self.assertEqual(annotate(self.store, path), 1)
        self.client.close()
        self.client = self.make_client(offline=True)
        inventory(self.store, self.client)
        self.assertEqual(self.client.requests, 0)
        self.assertEqual(len(self.calls), 2)
        self.assertTrue(inventory_rows(self.store)[0]['reviewed'])
        # Rebuilding the inventory from HTTP cache also makes zero requests.
        with self.store.db:
            self.store.db.execute("DELETE FROM checkpoints WHERE key='playlist_inventory'")
        inventory(self.store, self.client)
        self.assertEqual(self.client.cache_hits, 2)

    def test_budget_exhaustion_saves_partial_report_and_resumes(self):
        self.client.max_requests = 1
        with self.assertRaises(BudgetExceeded):
            inventory(self.store, self.client)
        self.assertEqual(self.store.get_checkpoint('playlist_inventory')['pages'], 1)
        self.assertTrue((self.store.folder / 'playlist_inventory.html').exists())
        self.client.close()
        self.client = self.make_client()
        inventory(self.store, self.client)
        self.assertEqual(len(self.calls), 2)

    def test_no_retry_on_quota_exhaustion_and_next_run_honors_cooldown(self):
        self.client.transport = lambda u: (403, {}, {'error': {'errors': [{'reason': 'quotaExceeded'}]}})
        with self.assertRaises(BudgetExceeded):
            inventory(self.store, self.client)
        self.assertEqual(self.client.requests, 1)
        self.client.close()
        self.client = self.make_client()
        with self.assertRaises(BudgetExceeded):
            inventory(self.store, self.client)
        self.assertEqual(self.client.requests, 0)

    def test_retries_are_bounded_counted_and_error_responses_cached(self):
        self.client.transport = lambda u: (503, {}, {'error': {'message': 'synthetic'}})
        with self.assertRaises(ResponseError):
            inventory(self.store, self.client)
        self.assertEqual(self.client.requests, 3)
        self.assertEqual(self.client.state.usage()[0]['attempts'], 3)
        self.assertGreaterEqual(self.client.state.db.execute('SELECT count(*) FROM http_results').fetchone()[0], 1)

    def test_refresh_retains_previous_results_and_labels(self):
        inventory(self.store, self.client)
        self.time += 10
        inventory(self.store, self.client, refresh=True)
        self.assertEqual(len(self.calls), 4)
        self.assertEqual(self.client.state.db.execute('SELECT count(*) FROM http_results').fetchone()[0], 4)

    def test_unknown_ids_rejected_atomically(self):
        inventory(self.store, self.client)
        path = Path(self.tmp.name) / 'annotations.json'
        path.write_text(json.dumps({'version': 1, 'playlists': [{'id': 'unknown'}]}))
        with self.assertRaises(ValueError):
            annotate(self.store, path)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM playlist_annotations').fetchone()[0], 0)

    def test_malformed_metadata_and_owner_changes_do_not_commit_partial_pages(self):
        self.client.transport = lambda u: (200, {}, {'items': [{'id': 'PLsynthetic', 'snippet': None}]})
        with self.assertRaises(ResponseError):
            inventory(self.store, self.client)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM entities').fetchone()[0], 0)
        self.client.transport = self.transport
        self.time += 10
        inventory(self.store, self.client, refresh=True)
        other = {'items': [{'id': 'PLother', 'snippet': {'channelId': 'UCbbbbbbbbbbbbbbbbbbbbbb'}}]}
        self.client.transport = lambda u: (200, {}, other)
        self.time += 10
        with self.assertRaises(ResponseError):
            inventory(self.store, self.client, refresh=True)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM entities').fetchone()[0], 3)

    def test_viewer_escapes_metadata_and_blocks_external_network(self):
        self.client.transport = lambda u: (200, {}, {'items': [{
            'id': 'PLsynthetic', 'snippet': {'title': '<script>unsafe()</script>', 'description': 'Synthetic'},
            'contentDetails': {'itemCount': 1}, 'status': {'privacyStatus': 'private'}}]})
        inventory(self.store, self.client)
        page = (self.store.folder / 'playlist_inventory.html').read_text()
        self.assertIn('&lt;script&gt;unsafe()', page)
        self.assertNotIn('<script>unsafe()', page)
        self.assertIn("connect-src 'none'", page)

    def test_pagination_cycle_stops_with_last_good_checkpoint(self):
        self.client.transport = lambda u: (200, {}, {'items': [], 'nextPageToken': 'cycle'})
        with self.assertRaises(ResponseError):
            inventory(self.store, self.client)
        self.assertEqual(self.store.get_checkpoint('playlist_inventory')['pages'], 1)


if __name__ == '__main__':
    unittest.main()
