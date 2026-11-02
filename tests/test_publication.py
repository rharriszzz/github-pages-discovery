import json
from pathlib import Path
import shutil
import tempfile
import unittest

from pagefinder.core import ROOT
from pagefinder.publication import check_publication, check_text, validate_public_inputs


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        shutil.copytree(ROOT / 'data', self.root / 'data')
        (self.root / 'docs').mkdir()
        (self.root / 'reports').mkdir()
        (self.root / 'docs/index.html').write_text('<p>Synthetic public catalog</p>')

    def tearDown(self):
        self.tmp.cleanup()

    def test_existing_public_catalog_passes(self):
        check_publication(ROOT)
        check_publication(self.root)

    def test_private_fields_and_secret_values_fail_before_export(self):
        path = self.root / 'data/sites.json'
        rows = json.loads(path.read_text())
        rows[0]['playlist_membership'] = ['synthetic-private']
        path.write_text(json.dumps(rows))
        with self.assertRaises(ValueError):
            validate_public_inputs(self.root)
        for value in ('{"refresh_token":"synthetic-secret"}', '{"visibility":"private"}',
                      'ya29.syntheticlongtokenmaterial', '/home/synthetic/.config/private'):
            with self.assertRaises(ValueError):
                check_text(value)

    def test_unreviewed_artifacts_and_symlinks_block_deployment(self):
        path = self.root / 'docs/playlist_inventory.html'
        path.write_text('Synthetic private playlist titles')
        with self.assertRaises(ValueError):
            check_publication(self.root)
        path.unlink()
        path.symlink_to(self.root / 'data/sites.json')
        with self.assertRaises(ValueError):
            check_publication(self.root)


if __name__ == '__main__':
    unittest.main()
