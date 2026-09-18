import unittest
from unittest.mock import patch
import test_assets
validator = test_assets.validator

class BaseAssetTests(unittest.TestCase):
    setUp = test_assets.AssetTests.setUp
    # Reuse directory scaffold only, not inherited frame tests.
    def test_optional_missing_bases(self):
        errors,pending=validator.validate_bases(self.root)
        self.assertEqual(errors,[])
        self.assertEqual(len(pending),4)

    def test_strict_requires_only_moa_pip(self):
        errors,pending=validator.validate_bases(self.root,True)
        self.assertEqual(len(errors),2)
        self.assertEqual(len(pending),2)

    def test_wrong_filename(self):
        (self.stage/'base.PNG').touch()
        self.assertTrue(any('filename' in e for e in validator.validate_bases(self.root)[0]))

    def test_present_base_uses_existing_full_png_validator(self):
        (self.stage/'base.png').touch()  # Empty invalid-file fixture, no generated image.
        self.assertTrue(validator.validate_bases(self.root)[0])
        for failure in ('dimensions must be 256x256','RGBA alpha channel required','invalid PNG'):
            with patch.object(validator,'png_errors',return_value=[failure]) as check:
                self.assertTrue(any(failure in e for e in validator.validate_bases(self.root)[0]))
                check.assert_called_once_with(self.stage/'base.png')
