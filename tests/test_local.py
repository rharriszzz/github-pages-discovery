from contextlib import closing, redirect_stderr, redirect_stdout
import errno
import io
import json
from pathlib import Path
import shutil
import sqlite3
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

    def test_startup_errors_are_actionable_without_leaking_private_details(self):
        private = 'PRIVATE_TITLE_TOKEN_PATH'
        cases = [
            (OSError(errno.EROFS, private, private), 'read-only', 'EROFS'),
            (PermissionError(errno.EACCES, private, private), 'Permission denied', 'EACCES'),
            (PermissionError(errno.EPERM, private, private), 'sandbox restrictions', 'EPERM'),
            (FileNotFoundError(errno.ENOENT, private, private), 'not found', 'ENOENT'),
            (OSError(errno.ENOSPC, private, private), 'No space left', 'ENOSPC'),
            (OSError(errno.EIO, private, private), 'Filesystem or local socket', 'EIO'),
            (OSError(private), 'Filesystem or local socket', ''),
            (sqlite3.OperationalError(private), 'Private SQLite operation failed', ''),
            (json.JSONDecodeError(private, private, 0), 'Check input format', ''),
        ]
        for exc, message, code in cases:
            with self.subTest(error=type(exc).__name__, code=code):
                with patch('pagefinder.local.Store', side_effect=exc):
                    result, out, err = self.invoke(['serve-creators'])
                self.assertEqual(result, 2)
                self.assertIn(message, err)
                self.assertIn(code, err)
                self.assertNotIn(private, out + err)
                self.assertNotIn(str(self.data), out + err)

    def test_busy_server_port_reports_recovery_and_closes_the_store(self):
        with patch('pagefinder.local.Store') as store, patch(
                'pagefinder.creator_server.serve_creators',
                side_effect=OSError(errno.EADDRINUSE, 'PRIVATE_SERVER_DETAILS')):
            result, out, err = self.invoke(['serve-creators', '--port', '8766'])
        self.assertEqual(result, 2)
        self.assertIn('EADDRINUSE', err)
        self.assertIn('--port 8767', err)
        self.assertNotIn('PRIVATE_SERVER_DETAILS', out + err)
        store.return_value.close.assert_called_once_with()

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
