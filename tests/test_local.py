from contextlib import closing, redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import shutil
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

from pagefinder.local import main
from pagefinder.youtube import SCOPE, authenticate


class LocalCLITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.data = self.folder / 'private'
        self.config = self.folder / 'config'
        self.base = ['--data-dir', str(self.data), '--config-dir', str(self.config)]

    def tearDown(self):
        self.tmp.cleanup()

    def invoke(self, args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            result = main(self.base + args)
        return result, out.getvalue(), err.getvalue()

    def test_missing_credentials_and_offline_miss_use_zero_api_attempts(self):
        result, out, err = self.invoke(['inventory'])
        self.assertEqual(result, 2)
        self.assertIn('authorization required', err)
        import sqlite3
        with closing(sqlite3.connect(self.data / 'http.sqlite3')) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM http_attempts').fetchone()[0], 0)
        result, out, err = self.invoke(['inventory', '--offline'])
        self.assertEqual(result, 2)
        self.assertIn('not cached', err)

    def test_import_and_coverage_cli_work_without_google_libraries(self):
        source = self.folder / 'history.json'
        shutil.copyfile(Path(__file__).parent / 'fixtures/takeout-v1/history.json', source)
        self.assertEqual(self.invoke(['init'])[0], 0)
        self.assertEqual(self.invoke(['import-takeout', str(source), '--kind', 'history'])[0], 0)
        result, out, err = self.invoke(['coverage'])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(out)['counts']['observations'], 4)
        self.assertEqual(self.invoke(['review', 'youtube:video:aaaaaaaaaaa', 'keep', '--reason', 'Synthetic method'])[0], 0)

    def test_auth_is_desktop_readonly_pkce_loopback_and_does_not_print_secrets(self):
        self.config.mkdir()
        (self.config / 'client_secret.json').write_text(json.dumps({'installed': {
            'client_id': 'synthetic', 'client_secret': 'synthetic',
            'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
            'token_uri': 'https://oauth2.googleapis.com/token'}}))
        credentials = Mock()
        credentials.granted_scopes = [SCOPE]
        credentials.to_json.return_value = '{"synthetic":"credentials"}'
        flow = Mock()
        flow.run_local_server.return_value = credentials
        factory = Mock(return_value=flow)
        module = types.ModuleType('google_auth_oauthlib.flow')
        module.InstalledAppFlow = types.SimpleNamespace(from_client_config=factory)
        with patch.dict('sys.modules', {'google_auth_oauthlib.flow': module}):
            result, out, err = self.invoke(['auth', '--port', '8765'])
        self.assertEqual(result, 0)
        self.assertEqual(factory.call_args.args[1], [SCOPE])
        self.assertTrue(factory.call_args.kwargs['autogenerate_code_verifier'])
        self.assertEqual(flow.run_local_server.call_args.kwargs['host'], '127.0.0.1')
        self.assertEqual(flow.run_local_server.call_args.kwargs['port'], 8765)
        self.assertEqual(flow.run_local_server.call_args.kwargs['authorization_prompt_message'], '')
        self.assertNotIn('synthetic', out + err)
        self.assertEqual((self.config / 'token.json').stat().st_mode & 0o777, 0o600)


if __name__ == '__main__':
    unittest.main()
