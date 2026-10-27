import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_alpha_assets import rgba_fixture, validator


class PngValidationCacheTests(unittest.TestCase):
    def setUp(self):
        validator._cached_png_errors.cache_clear()
        self.temp = tempfile.TemporaryDirectory(prefix='luma-png-cache-')
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'frame.png'

    def test_content_change_with_preserved_timestamp_invalidates_cache(self):
        self.path.write_bytes(rgba_fixture(alpha=255))
        stamp = self.path.stat()
        self.assertIn('transparent pixels required; fully opaque RGBA is invalid',
                      validator.png_errors(self.path, True))
        self.path.write_bytes(rgba_fixture(alpha=128))
        os.utime(self.path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        self.assertEqual(validator.png_errors(self.path, True), [])
        self.path.write_bytes(b'invalid')
        self.assertIn('invalid PNG signature', validator.png_errors(self.path, True))
        self.path.unlink()
        self.assertTrue(validator.png_errors(self.path, True))

    def test_identical_content_reuses_decode_and_outputs_are_independent(self):
        self.path.write_bytes(rgba_fixture(alpha=128))
        other = self.path.with_name('other.png')
        other.write_bytes(self.path.read_bytes())
        with patch.object(validator, '_decode_png_errors', wraps=validator._decode_png_errors) as decode:
            bounds, hashes = [], []
            errors = validator.png_errors(self.path, True, bounds, hashes)
            expected = (list(bounds), list(hashes))
            errors.append('caller mutation'); bounds.clear(); hashes.clear()
            self.assertEqual(validator.png_errors(other, True, bounds, hashes), [])
            self.assertEqual((bounds, hashes), expected)
            self.assertEqual(decode.call_count, 1)

    def test_all_filter_modes_match_uncached_decoder_and_option_contracts(self):
        for filtering in range(5):
            data = rgba_fixture(alpha=128, filtering=filtering)
            self.path.write_bytes(data)
            for transparency, want_bounds, want_hash in [(False,False,False), (False,True,False),
                    (True,True,False), (False,False,True), (True,True,True)]:
                a = [] if want_bounds else None
                b = [] if want_bounds else None
                h1 = [] if want_hash else None
                h2 = [] if want_hash else None
                expected = validator._decode_png_errors(data,transparency,a,h1)
                self.assertEqual(validator.png_errors(self.path,transparency,b,h2),expected)
                self.assertEqual(a,b);self.assertEqual(h1,h2)
        self.assertEqual(validator._cached_png_errors.cache_parameters()['maxsize'],128)
