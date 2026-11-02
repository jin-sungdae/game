"""Content cache must preserve validator semantics under mutable test fixtures."""
import os
import tempfile
import unittest
from pathlib import Path
from test_assets import validator, png, ROOT


class PngContentCacheTests(unittest.TestCase):
    def setUp(self):
        validator._png_result.cache_clear()

    def test_same_path_same_mtime_replacement_is_not_stale(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'candidate.png'
            path.write_bytes(png())
            stamp = path.stat().st_mtime_ns
            self.assertEqual(validator.png_errors(path), [])
            data = bytearray(path.read_bytes())
            data[-1] ^= 1  # Same length, corrupt CRC.
            path.write_bytes(data)
            os.utime(path, ns=(stamp,stamp))
            self.assertIn('PNG CRC mismatch', validator.png_errors(path))
            path.write_bytes(png())
            self.assertEqual(validator.png_errors(path), [])
            path.unlink()
            self.assertTrue(validator.png_errors(path))

    def test_outputs_are_independent_and_modes_remain_separate(self):
        path = ROOT/'design/production-batches/monsters/batch07/M061/base-v2.png'
        bounds, hashes = [], []
        errors = validator.png_errors(path, True, bounds, hashes)
        expected = (errors[:], bounds[:], hashes[:])
        errors.append('caller mutation');bounds.clear();hashes.clear()
        again_bounds, again_hashes = [], []
        self.assertEqual(validator.png_errors(path, True, again_bounds, again_hashes), expected[0])
        self.assertEqual((again_bounds, again_hashes), expected[1:])
        self.assertEqual(validator._png_result.cache_info().hits, 1)
        self.assertEqual(validator.png_errors(path), [])
        self.assertEqual(validator._png_result.cache_info().misses, 2)

    def test_cached_and_direct_decoder_agree_on_real_and_invalid_data(self):
        data_sets = [png(), png(128,256), b'bad PNG']
        data_sets.extend((ROOT/f'design/production-batches/monsters/batch07/M{i:03}/base-v2.png').read_bytes() for i in range(61,66))
        for data in data_sets:
            for transparency in (False,True):
                for need_bounds,need_hash in ((False,False),(True,False),(False,True),(True,True)):
                    bounds=[] if need_bounds else None
                    hashes=[] if need_hash else None
                    errors=validator._decode_png(data,transparency,bounds,hashes)
                    self.assertEqual(validator._png_result(data,transparency,need_bounds,need_hash),
                                     (tuple(errors),tuple(bounds or ()),tuple(hashes or ())))
        self.assertEqual(validator._png_result.cache_info().maxsize,1024)
