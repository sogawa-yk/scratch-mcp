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

client_path = os.path.join(os.path.dirname(__file__), '../src/4-2-client.py')
client_module = load_module("client_4_2", client_path)

class TestMCPClient_4_2(unittest.TestCase):
    def test_client_init_and_future(self):
        """Verify Client request tracking mechanism"""
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.stdout = MagicMock()
            mock_process.stdout.__iter__.return_value = iter([]) 
            mock_popen.return_value = mock_process
            
            client = client_module.MCPClient()
            
            # Test request ID increment
            # Just verify internal state for now
            self.assertTrue(hasattr(client, '_pending_requests'))
            self.assertEqual(client._request_id, 0)

            client.running = False


if __name__ == '__main__':
    unittest.main()
