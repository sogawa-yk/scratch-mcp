import sys
import os
import unittest
import importlib.util
from unittest.mock import MagicMock, patch

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

app_path = os.path.join(os.path.dirname(__file__), '../src/6-1-app_oci.py')
app_module = load_module("app_6_1_oci", app_path)

class TestApp_6_1_OCI(unittest.TestCase):
    def test_clean_json_text_helper(self):
        """Test helper directly"""
        raw = '```json\n{"a": 1}\n```'
        cleaned = app_module.clean_json_text(raw)
        self.assertEqual(cleaned, '{"a": 1}')

if __name__ == '__main__':
    unittest.main()
