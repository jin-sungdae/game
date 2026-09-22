"""Approved immutable remaining delivery, validated by the existing asset gate."""
import hashlib
import unittest
import test_assets

HASHES = {'PEBB': '52069d2ed348e74d7387ccf07df7c725c2b82400016b6576dd1f28c6cf023ca4', 'PUFF': '8e4414e08d8e1a89a10eff7af0275b72b63eddda3d563d44abd7299c1887984d', 'TIKKI': 'd234b8bc08e62802d1fe684176208ecd91a798d57d959f2ec9153699a6db8a81', 'MIMI': 'b6476e6e585ef6075c131d1fa227304f39a738e87044e71694f3fdee12c41479', 'WISP': '9423d6524797e82349ab9f0bf40a4f8be5dacb3683276c0645516c52388e1b3d', 'SHADE': '3d2c8330486a197e30d8dc54d2f1b11de2458f982cb00f74ef73c06d4fc72974', 'EMBER': 'a2ea1e16f29e383c6ad29505d8d6ce65750fa11a8216cfb0fde470b5e2cb9f66', 'LUNET': 'eeba6eeec884e042b32f151f26b5e881a2dd0d3db65a5ba0ef13bf6153765640', 'NOVA': '0fd29358f313abafd9286357d57d43aac1114661c2b7f40e75596dd9b744b2a6', 'NOCT': 'c808c729d22318b7cb544682ce629d2b35eda07f4d199c288b6210ab4c3ba75a'}

class RemainingAssets(unittest.TestCase):
    def test_approved_source_bytes(self):
        for code, digest in HASHES.items():
            with self.subTest(code=code):
                path = test_assets.ROOT / 'public/assets/monsters' / code.lower() / 'base.png'
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)

    def test_all_fifteen_real_assets_pass_strict_gate(self):
        self.assertEqual(test_assets.validator.validate_alpha(test_assets.ROOT, strict=True), ([], []))
