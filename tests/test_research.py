from pathlib import Path
import sqlite3
import tempfile
import unittest

from pagefinder.core import ROOT
from pagefinder.privacy import outside_repo, private_write
from pagefinder.research import Store


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name) / 'private'
        self.store = Store(self.folder)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_private_paths_reject_repository_ancestors_symlinks_and_other_repos(self):
        for path in (ROOT, ROOT / 'docs/private', ROOT / '.cache/private', ROOT.parent):
            with self.assertRaises(ValueError):
                outside_repo(path)
        link = Path(self.tmp.name) / 'linked'
        link.symlink_to(ROOT, target_is_directory=True)
        with self.assertRaises(ValueError):
            outside_repo(link / 'docs/private')
        repo = Path(self.tmp.name) / 'other'
        repo.mkdir()
        (repo / '.git').write_text('gitdir: synthetic')
        with self.assertRaises(ValueError):
            outside_repo(repo / 'private')

    def test_migration_is_idempotent_and_future_version_is_refused(self):
        self.assertEqual(self.store.db.execute('PRAGMA user_version').fetchone()[0], 1)
        second = Store(self.folder)
        second.close()
        self.store.db.execute('PRAGMA user_version=2')
        with self.assertRaises(ValueError):
            Store(self.folder)

    def test_provenance_titles_and_manual_review_survive_recomputation(self):
        with self.store.db:
            eid = self.store.evidence('synthetic', 'test', completeness='bounded_export')
            self.store.entity('test:1', 'video', '1', 'Old title', eid)
        self.store.review('test:1', 'keep', 'Useful method')
        with self.store.db:
            newer = self.store.evidence('synthetic', 'test-new')
            self.store.entity('test:1', 'video', '1', 'New title', newer, visibility='public')
        titles = {r[0] for r in self.store.db.execute('SELECT title FROM titles')}
        self.assertEqual(titles, {'Old title', 'New title'})
        self.assertEqual(self.store.db.execute('SELECT decision FROM reviews').fetchone()[0], 'keep')
        self.assertEqual(self.store.db.execute('SELECT visibility FROM entities').fetchone()[0], 'private')
        with self.assertRaises(sqlite3.IntegrityError):
            with self.store.db:
                self.store.evidence('synthetic', 'invalid', confidence=1.1)

    def test_unknown_metrics_and_permissions_are_explicit(self):
        self.assertEqual(self.store.coverage()['watch_minutes'], 'not_measurable')
        private_write(self.folder / 'a.txt', b'synthetic')
        self.assertEqual((self.folder / 'a.txt').stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.folder.stat().st_mode & 0o777, 0o700)


if __name__ == '__main__':
    unittest.main()
