import unittest
from unittest.mock import patch
import test_assets
v=test_assets.validator
class ReleaseAssets(unittest.TestCase):
    def test_all_eighteen_required_bases_decode_with_nonempty_alpha_bounds(self):
        errors,rows=v.validate_release()
        self.assertEqual(errors,[]);self.assertEqual(len(rows),18)
        for row in rows:
            x0,y0,x1,y1=row['bounds']
            self.assertTrue(0<=x0<=x1<256 and 0<=y0<=y1<256,row)
    def test_missing_required_base_blocks_release(self):
        with patch.object(v,'png_errors',return_value=['missing required base']):
            errors,_=v.validate_release()
            self.assertTrue(errors)
