import os
import unittest
from unittest.mock import patch
import config


class ConfigValidationTests(unittest.TestCase):
    def test_validate_config_fails_loudly_when_required_vars_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError) as ctx:
                config.validate_config(required_vars=["MISSING_KEY_A", "MISSING_KEY_B"], allow_skip=False)
            err_msg = str(ctx.exception)
            self.assertIn("MISSING_KEY_A", err_msg)
            self.assertIn("MISSING_KEY_B", err_msg)
            self.assertIn("Configuration error", err_msg)

    def test_validate_config_passes_when_all_required_present(self):
        with patch.dict(os.environ, {"KEY1": "val1", "KEY2": "val2"}, clear=True):
            missing = config.validate_config(required_vars=["KEY1", "KEY2"], allow_skip=False)
            self.assertEqual(missing, [])

    def test_validate_config_allows_skip_env_var(self):
        with patch.dict(os.environ, {"NEXUS_SKIP_ENV_VALIDATION": "1"}, clear=True):
            missing = config.validate_config(required_vars=["NOT_SET_KEY"], allow_skip=True)
            self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
