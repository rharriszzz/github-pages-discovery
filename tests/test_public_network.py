import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.request import Request

from pagefinder import core


class Response(io.BytesIO):
    def __init__(self, body, headers=None, status=200):
        super().__init__(body)
        self.headers = headers or {}
        self.status = status


class PublicNetworkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.root_patch = patch.object(core, 'ROOT', self.root)
        self.root_patch.start()
        self.token_patch = patch.object(core, 'github_token', return_value=None)
        self.token_patch.start()

    def tearDown(self):
        self.token_patch.stop()
        self.root_patch.stop()
        self.tmp.cleanup()

    def test_github_response_cached_and_offline_rerun_makes_no_request(self):
        opener = Mock()
        opener.open.return_value = Response(b'{"items":[]}', {'ETag': 'synthetic'})
        with patch.object(core, 'build_opener', return_value=opener):
            client = core.GitHubClient(delay=0)
            try:
                self.assertEqual(client.get('/search/repositories', {'q': 'synthetic'}), {'items': []})
                self.assertEqual(client.get('/search/repositories', {'q': 'synthetic'}), {'items': []})
                self.assertEqual(opener.open.call_count, 1)
                usage = {u['service']: u['attempts'] for u in client.network.usage()}
                self.assertEqual(usage, {'github_core': 1, 'github_search': 1})
                client.offline = True
                self.assertEqual(client.get('/search/repositories', {'q': 'synthetic'}), {'items': []})
            finally:
                client.network.close()

    def test_github_rate_response_cached_and_next_request_blocked(self):
        opener = Mock()
        opener.open.side_effect = HTTPError('https://api.github.com/test', 429, 'synthetic',
                                            {'Retry-After': '120'}, io.BytesIO(b'{"message":"synthetic"}'))
        with patch.object(core, 'build_opener', return_value=opener):
            client = core.GitHubClient(delay=0)
            try:
                with self.assertRaises(core.RateLimited):
                    client.get('/test')
                with self.assertRaises(core.RateLimited):
                    client.get('/different')
                self.assertEqual(opener.open.call_count, 1)
                self.assertEqual(client.network.cached('https://api.github.com/test')['status'], 429)
            finally:
                client.network.close()

    def test_site_robots_and_html_cached_and_offline_outcome_preserved(self):
        opener = Mock()
        opener.open.side_effect = [Response(b'User-agent: *\nAllow: /', {'Content-Type': 'text/plain'}),
                                   Response(b'<title>Synthetic</title><p>Hello</p>', {'Content-Type': 'text/html'})]
        with patch.object(core, 'build_opener', return_value=opener):
            fetcher = core.PageFetcher(delay=0)
            try:
                with patch.object(fetcher.network, 'admit') as admit:
                    result = fetcher.fetch('https://synthetic.github.io/')
                self.assertEqual(result['title'], 'Synthetic')
                self.assertEqual(admit.call_count, 4)  # global + per-host for robots and HTML
                self.assertIsNotNone(fetcher.network.cached('https://synthetic.github.io/robots.txt'))
                self.assertIsNotNone(fetcher.network.cached('https://synthetic.github.io/'))
                fetcher.offline = True
                self.assertEqual(fetcher.fetch('https://synthetic.github.io/'), result)
                self.assertEqual(opener.open.call_count, 2)
            finally:
                fetcher.network.close()

    def test_enrichment_does_not_swallow_rate_limit(self):
        path = self.root / 'sites.json'
        path.write_text(json.dumps([{'url': 'https://synthetic.github.io/', 'owner': 'synthetic'}]))
        with patch.object(core, 'DB', path), patch.object(core, 'GitHubClient') as api, patch.object(core, 'PageFetcher') as pages:
            api.return_value.get.side_effect = core.RateLimited('Synthetic limit')
            with self.assertRaises(core.RateLimited):
                core.enrich()
            pages.return_value.fetch.assert_not_called()

    def test_redirects_are_bounded_confined_and_counted(self):
        admit = Mock()
        handler = core.GitHubRedirects(admit)
        req = Request('https://api.github.com/old')
        redirected = handler.redirect_request(req, None, 301, 'moved', {}, 'https://api.github.com/new')
        self.assertEqual(redirected.full_url, 'https://api.github.com/new')
        admit.assert_called_once_with('/new')
        with self.assertRaises(core.ApiError):
            handler.redirect_request(req, None, 301, 'moved', {}, 'https://external.test/credentials')
        site_admit = Mock()
        site = core.NoExternalRedirects(site_admit)
        site.redirect_request(Request('https://synthetic.github.io/old'), None, 301, 'moved', {},
                              'https://synthetic.github.io/new')
        site_admit.assert_called_once_with('https://synthetic.github.io/new')


if __name__ == '__main__':
    unittest.main()
