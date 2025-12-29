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

client_path = os.path.join(os.path.dirname(__file__), '../src/6-1-client.py')
client_module = load_module("client_6_1", client_path)

class TestMCPClient_6_1(unittest.TestCase):
    def test_client_structure(self):
        """Verify Client class structure"""
        client = client_module.MCPClient
        self.assertTrue(hasattr(client, 'send_request'))
        self.assertTrue(hasattr(client, 'send_notification'))

if __name__ == '__main__':
    unittest.main()
