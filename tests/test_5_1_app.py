import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import importlib.util

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

app_path = os.path.join(os.path.dirname(__file__), '../src/5-1-app.py')
app_module = load_module("app_5_1", app_path)

class TestApp_5_1(unittest.TestCase):
    def test_mock_llm_decision(self):
        """Test the mock LLM logic regex"""
        # Test 1: No numbers
        res = app_module.mock_llm_decision("こんにちは")
        self.assertFalse(res["use_tool"])
        
        # Test 2: Add intent with numbers
        res = app_module.mock_llm_decision("10と20を足して")
        self.assertTrue(res["use_tool"])
        self.assertEqual(res["tool_name"], "add_numbers")
        self.assertEqual(res["tool_args"], {"a": 10, "b": 20})
        
        # Test 3: Add intent without enough numbers
        res = app_module.mock_llm_decision("計算して 10")
        self.assertFalse(res["use_tool"])

if __name__ == '__main__':
    unittest.main()
