import hashlib
import json
import struct
import unittest
import zlib
import test_assets

ROOT = test_assets.ROOT
SHA = '32b21b0b2f0b0c3c2e9172f4f797431e3be369eae93142c2482ecccf6d0db588'

def alpha_bounds(data):
    offset, compressed = 8, bytearray()
    while offset < len(data):
        size = struct.unpack('>I', data[offset:offset+4])[0]
        if data[offset+4:offset+8] == b'IDAT': compressed.extend(data[offset+8:offset+8+size])
        offset += size+12
    raw = zlib.decompress(compressed)
    previous, points = bytearray(1024), []
    for y in range(256):
        start = y*1025
        filtering, row = raw[start], bytearray(raw[start+1:start+1025])
        for i in range(1024):
            left, above, corner = row[i-4] if i>=4 else 0, previous[i], previous[i-4] if i>=4 else 0
            p=left+above-corner
            distances=[abs(p-left),abs(p-above),abs(p-corner)]
            predictor=[0,left,above,(left+above)//2,(left,above,corner)[distances.index(min(distances))]][filtering]
            row[i]=(row[i]+predictor)&255
        points.extend((x,y) for x,a in enumerate(row[3::4]) if a)
        previous=row
    return min(x for x,y in points),min(y for x,y in points),max(x for x,y in points),max(y for x,y in points)

class NeblaAssetTests(unittest.TestCase):
    def test_approved_bytes_rgba_transparency_and_bounds(self):
        path=ROOT/'public/assets/creatures/moa/stage03/base.png'
        data=path.read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(),SHA)
        self.assertEqual(test_assets.validator.png_errors(path,True),[])
        self.assertEqual(alpha_bounds(data),(30,24,232,250))
    def test_registry_separates_production_base_from_unsupplied_animation(self):
        moa=json.loads((ROOT/'src/entities/companions.json').read_text())['moa']
        self.assertEqual(moa['stageNames']['3'],'NEBLA')
        self.assertEqual(moa['stageAssetStatus']['3'],'PRODUCTION_BASE')
        self.assertEqual(moa['stageAnimationStatus']['3'],'NOT_SUPPLIED')
        self.assertFalse((ROOT/'public/assets/creatures/moa/stage03/manifest.json').exists())
    def test_native_panel_canvas_anchor_and_mirrored_alpha_bounds(self):
        # Pixel extents use exclusive maxima; mirroring preserves canvas/anchor, not asymmetrical ink centroid.
        scale=82/256
        right=(7+30*scale,22+24*scale,7+233*scale,22+251*scale)
        left=(7+(256-233)*scale,right[1],7+(256-30)*scale,right[3])
        for box in (right,left):
            self.assertGreaterEqual(box[0],0);self.assertLessEqual(box[2],96)
            self.assertGreaterEqual(box[1],0);self.assertLessEqual(box[3],104)
        self.assertAlmostEqual(right[2]-right[0],left[2]-left[0])
        self.assertEqual(7+82/2,48);self.assertEqual(22+82,104)
