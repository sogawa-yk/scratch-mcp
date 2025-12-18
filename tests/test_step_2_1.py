import subprocess
import sys
import os
import json

def test_resources():
    server_path = os.path.join(os.path.dirname(__file__), '../src/2-1-server.py')
    
    # 1. Initialize (Check capabilities)
    init_request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}},
        "id": 1
    }
    
    # 2. List Resources
    list_request = {
        "jsonrpc": "2.0",
        "method": "resources/list",
        "id": 2
    }
    
    # 3. Read Resource
    read_request = {
        "jsonrpc": "2.0",
        "method": "resources/read",
        "params": {"uri": "memo://welcome"},
        "id": 3
    }
    
    full_input = json.dumps(init_request) + "\n" + json.dumps(list_request) + "\n" + json.dumps(read_request) + "\n"
    
    print("--- Testing Static Resources ---")
    
    process = subprocess.Popen(
        [sys.executable, server_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    stdout, stderr = process.communicate(input=full_input, timeout=2)
    
    responses = stdout.strip().split('\n')
    if len(responses) != 3:
        print(f"❌ Expected 3 responses, got {len(responses)}")
        print(f"Stdout: {stdout}")
        return

    # Check Capabilities
    try:
        resp1 = json.loads(responses[0])
        caps = resp1.get("result", {}).get("capabilities", {})
        if "resources" in caps:
            print("✅ Capabilities include 'resources' (Correct)")
        else:
            print(f"❌ Capabilities missing 'resources': {caps}")
    except:
        print("❌ Failed to parse init response")

    # Check List Resources
    try:
        resp2 = json.loads(responses[1])
        resources = resp2.get("result", {}).get("resources", [])
        if len(resources) == 1 and resources[0]["uri"] == "memo://welcome":
            print("✅ resources/list returned correct resource (Correct)")
        else:
            print(f"❌ resources/list invalid: {resources}")
    except:
        print("❌ Failed to parse list response")

    # Check Read Resource
    try:
        resp3 = json.loads(responses[2])
        contents = resp3.get("result", {}).get("contents", [])
        if len(contents) > 0 and "Welcome" in contents[0].get("text", ""):
            print("✅ resources/read returned correct content (Correct)")
        else:
            print(f"❌ resources/read invalid: {contents}")
    except:
        print("❌ Failed to parse read response")

if __name__ == "__main__":
    test_resources()
