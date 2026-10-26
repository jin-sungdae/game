import hashlib
import tempfile
import unittest
from pathlib import Path
from test_assets import png, validator
from test_alpha_assets import rgba_fixture


class PngContentCacheTests(unittest.TestCase):
    def test_content_mutation_deletion_and_output_mutation_do_not_reuse_stale_results(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'base.png'
            path.write_bytes(rgba_fixture(128))
            bounds, hashes = [], []
            self.assertEqual(validator.png_errors(path, True, bounds, hashes), [])
            expected_bounds, expected_hashes = list(bounds), list(hashes)
            bounds.clear(); hashes.clear()
            self.assertEqual(validator.png_errors(path, True, bounds, hashes), [])
            self.assertEqual((bounds, hashes), (expected_bounds, expected_hashes))
            path.write_bytes(rgba_fixture(255))
            self.assertIn('transparent pixels required; fully opaque RGBA is invalid', validator.png_errors(path, True))
            path.write_bytes(png(128, 256))
            self.assertIn('dimensions must be 256x256', validator.png_errors(path, True))
            path.unlink()
            self.assertTrue(validator.png_errors(path, True))

    def test_all_filters_preserve_decoded_hash_bounds_and_transparency(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'base.png'
            expected = hashlib.sha256(bytes([20, 40, 60, 128]) * 256 * 256).hexdigest()
            for mode in range(5):
                path.write_bytes(rgba_fixture(128, mode))
                bounds, hashes = [], []
                self.assertEqual(validator.png_errors(path, True, bounds, hashes), [])
                self.assertEqual(bounds, [0, 0, 255, 255])
                self.assertEqual(hashes, [expected])
            self.assertEqual(validator._png_errors_bytes.cache_info().maxsize, 256)
