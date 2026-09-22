"""Immutable approved Batch 1 delivery; no image generation or gameplay activation."""
import hashlib
import json
import unittest
import test_assets

ROOT = test_assets.ROOT
DELIVERIES = {
    'MELLO': ('818efb32f7e5a19efcbb87342eb07b55047cd99e15d02dd30f47bca03c85a831', 'SLIME', 'JUMP', 'CURIOUS', 'BOTTOM'),
    'MOSSY': ('6555280c8dc76d8b93ddd348cae1fbf7b27e282bd0bb6bfbec235dcc874afdb1', 'PLANT', 'GROUND', 'SLEEPY', 'LOWER_CORNER'),
    'CHIRP': ('8629ba2cf4f22f3e0946f7d3e030869ce5f38f5a06f2f65ca9af77c14bfba83e', 'BIRD', 'FLYING', 'CURIOUS', 'TOP'),
    'BUBU': ('979f8a38cc19cc5d3425aebe65142c559466b9ad32d3406f60646dfa1ba6eed4', 'AQUATIC', 'JUMP', 'PLAYFUL', 'BOTTOM'),
}

class Batch1Assets(unittest.TestCase):
    def test_original_bytes_format_alpha_and_canonical_identity(self):
        registry=json.loads((ROOT/'src/entities/monsters.json').read_text())
        for code,(digest,*_) in DELIVERIES.items():
            with self.subTest(code=code):
                url=f'/assets/monsters/{code.lower()}/base.png'
                self.assertEqual(registry[code]['baseAsset'],url)
                image=ROOT/'public'/url.lstrip('/')
                self.assertEqual(hashlib.sha256(image.read_bytes()).hexdigest(),digest)
                self.assertEqual(test_assets.validator.png_errors(image,require_transparency=True),[])

    def test_approved_metadata_and_separate_readiness_activation(self):
        content=json.loads((ROOT/'src/entities/monster-dex.json').read_text())
        for code,(_,archetype,movement,behavior,zone) in DELIVERIES.items():
            with self.subTest(code=code):
                m=next(m for m in content if m['monsterCode']==code)
                self.assertEqual([m[k] for k in ['rarity','archetype','movementProfile','behaviorProfile','spawnProfile']],['COMMON',archetype,movement,behavior,zone])
                self.assertEqual(m['assetIdentity'],code.lower())
                self.assertTrue(m['enabled'])
                self.assertTrue(m['contentReady'])
                self.assertEqual(m['productionStatus'],'PRODUCTION')
        self.assertEqual([m['monsterCode'] for m in content if m['enabled']],['PIP','MELLO','MOSSY','CHIRP','BUBU'])

    def test_delivered_four_and_pip_never_missing(self):
        errors,pending=test_assets.validator.validate_alpha(ROOT)
        self.assertEqual(errors,[])
        strict_errors,_=test_assets.validator.validate_alpha(ROOT,True)
        for code in [*DELIVERIES,'PIP']:
            self.assertFalse(any(f'/monsters/{code.lower()}/' in line for line in pending+strict_errors))
        pip=ROOT/'public/assets/monsters/pip/base.png'
        self.assertEqual(test_assets.validator.png_errors(pip,require_transparency=True),[])
