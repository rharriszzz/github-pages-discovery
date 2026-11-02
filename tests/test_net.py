from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import unittest

from pagefinder.net import BudgetExceeded, NetworkState, next_quota_day, quota_day


class NetworkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'network.sqlite3'
        self.time = 1700000000.0
        self.state = NetworkState(self.path, clock=lambda: self.time)

    def tearDown(self):
        self.state.close()
        self.tmp.cleanup()

    def test_budget_persists_and_is_shared_between_process_connections(self):
        self.assertEqual(self.state.reserve('test', interval=0, window=60, limit=1), 0)
        other = NetworkState(self.path, clock=lambda: self.time)
        try:
            with self.assertRaises(BudgetExceeded):
                other.reserve('test', interval=0, window=60, limit=1)
        finally:
            other.close()
        self.time += 61
        self.assertEqual(self.state.reserve('test', interval=0, window=60, limit=1), 0)

    def test_pacing_does_not_reserve_before_request_admission(self):
        self.state.reserve('test', interval=2)
        self.time += .5
        self.assertEqual(self.state.reserve('test', interval=2), 1.5)
        self.assertEqual(self.state.usage()[0]['attempts'], 1)

    def test_concurrent_clients_cannot_overspend_one_budget(self):
        def spend(_):
            state = NetworkState(self.path, clock=lambda: self.time)
            try:
                state.reserve('shared', interval=0, limit=2)
                return True
            except BudgetExceeded:
                return False
            finally:
                state.close()
        with ThreadPoolExecutor(max_workers=5) as pool:
            admitted = list(pool.map(spend, range(5)))
        self.assertEqual(sum(admitted), 2)

    def test_daily_quota_resets_at_pacific_midnight(self):
        self.state.reserve('youtube', interval=0, daily_units=1)
        with self.assertRaises(BudgetExceeded):
            self.state.reserve('youtube', interval=0, daily_units=1)
        previous = quota_day(self.time)
        self.time = next_quota_day(self.time)
        self.assertNotEqual(previous, quota_day(self.time))
        self.state.reserve('youtube', interval=0, daily_units=1)
        # Spring DST day is 23 hours, not a fixed 86400 seconds.
        stamp = datetime(2024, 3, 10, 8, tzinfo=timezone.utc).timestamp()
        self.assertEqual(next_quota_day(stamp) - stamp, 23 * 3600)

    def test_cooldown_headers_persist_and_are_honored(self):
        self.state.response_limits('test', 429, {'Retry-After': '120'})
        with self.assertRaises(BudgetExceeded):
            self.state.reserve('test')
        self.time += 121
        self.state.response_limits('test', 200, {'X-RateLimit-Remaining': '0',
                                              'X-RateLimit-Reset': str(self.time + 3600)})
        with self.assertRaises(BudgetExceeded):
            self.state.reserve('test')

    def test_every_response_version_cached_without_sensitive_headers(self):
        url = 'https://example.test/api'
        self.state.save(url, 200, {'ETag': 'v1', 'Authorization': 'secret', 'Set-Cookie': 'secret'}, {'n': 1})
        self.time += 1
        self.state.save(url, 503, {}, {'error': 'synthetic'})
        self.assertEqual(self.state.cached(url)['status'], 503)
        self.assertEqual(self.state.db.execute('SELECT count(*) FROM http_results').fetchone()[0], 2)
        self.assertNotIn('secret', str(self.state.db.execute('SELECT headers FROM http_results').fetchall()))


if __name__ == '__main__':
    unittest.main()
