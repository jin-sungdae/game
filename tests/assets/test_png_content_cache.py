"""Cache equivalence and invalidation; the existing decoder remains authoritative."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_assets import validator, png
from test_alpha_assets import rgba_fixture


class PngContentCacheTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'frame.png'
        validator._cached_png_result.cache_clear()

    def test_same_bytes_reuse_decoder_and_replay_output_appends(self):
        data = rgba_fixture(alpha=50, filtering=4)
        self.path.write_bytes(data)
        with patch.object(validator, '_decode_png', wraps=validator._decode_png) as decode:
            expected_bounds, expected_hashes = [], []
            self.assertEqual(validator.png_errors(self.path, True, expected_bounds, expected_hashes), [])
            other = self.path.with_name('copy.png'); other.write_bytes(data)
            bounds, hashes = ['prefix'], ['prefix']
            self.assertEqual(validator.png_errors(other, True, bounds, hashes), [])
            self.assertEqual(bounds, ['prefix'] + expected_bounds)
            self.assertEqual(hashes, ['prefix'] + expected_hashes)
            self.assertEqual(decode.call_count, 1)

    def test_same_path_changed_content_is_revalidated(self):
        self.path.write_bytes(rgba_fixture(alpha=50))
        self.assertEqual(validator.png_errors(self.path, True), [])
        self.path.write_bytes(rgba_fixture(alpha=255))
        self.assertIn('transparent pixels required; fully opaque RGBA is invalid',
                      validator.png_errors(self.path, True))
        self.path.unlink()
        self.assertTrue(validator.png_errors(self.path, True))
        self.path.write_bytes(rgba_fixture(alpha=50))
        self.assertEqual(validator.png_errors(self.path, True), [])

    def test_option_combinations_equal_uncached_decoder(self):
        for data in (png(), rgba_fixture(alpha=255, filtering=2), b'not a png'):
            self.path.write_bytes(data)
            for transparency in (False, True):
                for with_bounds in (False, True):
                    for with_hashes in (False, True):
                        a = [] if with_bounds else None; b = [] if with_hashes else None
                        c = [] if with_bounds else None; d = [] if with_hashes else None
                        expected = validator._decode_png(data, transparency, a, b)
                        actual = validator.png_errors(self.path, transparency, c, d)
                        self.assertEqual((actual, c, d), (expected, a, b))
                        actual.append('caller mutation')
                        self.assertEqual(validator.png_errors(self.path, transparency,
                            [] if with_bounds else None, [] if with_hashes else None), expected)

    def test_large_input_not_retained_and_cache_bounded(self):
        data = b'x' * (256 * 1024 + 1); self.path.write_bytes(data)
        self.assertEqual(validator.png_errors(self.path), validator._decode_png(data))
        self.assertEqual(validator._cached_png_result.cache_info().currsize, 0)
        for i in range(520):
            self.path.write_bytes(('invalid-'+str(i)).encode())
            validator.png_errors(self.path)
        self.assertEqual(validator._cached_png_result.cache_info().currsize, 512)
