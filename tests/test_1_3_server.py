import subprocess
import sys
import os
import json

def test_handshake():
    server_path = os.path.join(os.path.dirname(__file__), '../src/1-3-server.py')
    
    # 1. Initialize
    init_request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}},
        "id": 1
    }
    
    # 2. Initialized Notification
    initialized_notif = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    }
    
    # 3. Ping
    ping_request = {
        "jsonrpc": "2.0",
        "method": "ping",
        "id": 2
    }
    
    full_input = json.dumps(init_request) + "\n" + json.dumps(initialized_notif) + "\n" + json.dumps(ping_request) + "\n"
    
    print("--- Testing Handshake & Dispatcher ---")
    
    process = subprocess.Popen(
        [sys.executable, server_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    stdout, stderr = process.communicate(input=full_input, timeout=2)
    
    # Verify STDERR logs
    if "Connection initialized successfully." in stderr:
        print("✅ Found 'initialized' log (Correct)")
    else:
        print("❌ Missing 'initialized' log")
        
    # Verify STDOUT responses
    responses = stdout.strip().split('\n')
    if len(responses) != 2:
        print(f"❌ Expected 2 responses (Initialize + Ping), got {len(responses)}")
        print(f"Stdout content: {stdout!r}")
        return

    # Parse and check Initialize Response
    try:
        resp1 = json.loads(responses[0])
        if resp1.get("id") == 1 and "serverInfo" in resp1.get("result", {}):
            print("✅ Initialize Response valid (Correct)")
        else:
            print(f"❌ Initialize Response invalid: {resp1}")
    except json.JSONDecodeError:
        print(f"❌ Failed to parse response 1: {responses[0]}")

    # Parse and check Ping Response
    try:
        resp2 = json.loads(responses[1])
        if resp2.get("id") == 2 and resp2.get("result") == {}:
            print("✅ Ping Response valid (Correct)")
        else:
            print(f"❌ Ping Response invalid: {resp2}")
    except json.JSONDecodeError:
        print(f"❌ Failed to parse response 2: {responses[1]}")

if __name__ == "__main__":
    test_handshake()
