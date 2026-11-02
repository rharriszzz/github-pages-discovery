import unittest
from pagefinder.core import safe_site, repo_site_urls, score, PageText


class CoreTests(unittest.TestCase):
    def test_site_url_restriction(self):
        self.assertIsNotNone(safe_site('https://example.github.io/hello/'))
        for url in ('http://example.github.io/', 'https://example.github.io.evil.test/',
                    'https://example.org/', 'https://user:pass@example.github.io/',
                    'https://foo.github.io/a/../secret', 'https://foo.github.io/?u=1'):
            self.assertIsNone(safe_site(url), url)

    def test_user_site(self):
        repo = {'owner': {'login': 'Jane'}, 'name': 'jane.github.io', 'has_pages': True}
        self.assertEqual(repo_site_urls(repo), ['https://jane.github.io/'])

    def test_project_site_only_if_pages_true(self):
        repo = {'owner': {'login': 'Jane'}, 'name': 'science', 'has_pages': True}
        self.assertEqual(repo_site_urls(repo), ['https://jane.github.io/science/'])
        repo['has_pages'] = False
        self.assertEqual(repo_site_urls(repo), [])

    def test_invalid_homepage_is_not_included(self):
        repo = {'owner': {'login': 'Jane'}, 'name': 'science', 'has_pages': True,
                'homepage': 'https://internal.example.com/private'}
        self.assertEqual(repo_site_urls(repo), ['https://jane.github.io/science/'])

    def test_score_explanations(self):
        row = {'title': 'Navier-Stokes and vortex dynamics', 'summary': 'A numerical vortex solver'}
        interests = [{'name': 'Fluids', 'weight': 5, 'terms': ['navier-stokes', 'vortex']},
                     {'name': 'Music', 'weight': 5, 'terms': ['midi']}]
        actual = score(row, interests)
        self.assertGreater(actual['score'], 0)
        self.assertEqual(actual['interests'], ['Fluids'])
        self.assertEqual(actual['evidence'][0]['matches'][0]['term'], 'navier-stokes')

    def test_parse_site(self):
        parser = PageText()
        parser.feed('<title>Fluid Science</title><meta name="description" content="Examples"><script>secret text</script><main>Hello world</main>')
        self.assertEqual(parser.description, 'Examples')
        self.assertNotIn('secret', ' '.join(parser.text_parts))
        self.assertIn('Hello', ' '.join(parser.text_parts))


if __name__ == '__main__':
    unittest.main()
