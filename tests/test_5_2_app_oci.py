import sys
import os
import unittest
import json
import importlib.util
from unittest.mock import MagicMock, patch

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

app_path = os.path.join(os.path.dirname(__file__), '../src/5-2-app_oci.py')
app_module = load_module("app_5_2_oci", app_path)

class TestApp_5_2_OCI(unittest.TestCase):
    def test_clean_json_text(self):
        """Test JSON markdown cleaner"""
        # Case 1: Plain JSON
        raw = '{"key": "value"}'
        cleaned = app_module.clean_json_text(raw)
        self.assertEqual(cleaned, raw)
        
        # Case 2: Markdown block
        raw = '```json\n{"key": "value"}\n```'
        cleaned = app_module.clean_json_text(raw)
        self.assertEqual(cleaned, '{"key": "value"}')
        
        # Case 3: Markdown without language
        raw = '```\n{"key": "value"}\n```'
        cleaned = app_module.clean_json_text(raw)
        self.assertEqual(cleaned, '{"key": "value"}')

    def test_agent_decision_model(self):
        """Test Pydantic model"""
        data = {
            "thought": "Thinking...",
            "use_tool": True,
            "tool_name": "test_tool",
            "tool_args": {"x": 1}
        }
        model = app_module.AgentDecision(**data)
        self.assertEqual(model.tool_name, "test_tool")

if __name__ == '__main__':
    unittest.main()
