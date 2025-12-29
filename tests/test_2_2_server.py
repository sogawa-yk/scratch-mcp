import subprocess
import sys
import os
import json

def test_tools():
    # 2-2-server.py is the precursor to 3-1-server.py (renamed from 2-3).
    # It should have tools capability but maybe not all the refinements.
    server_path = os.path.join(os.path.dirname(__file__), '../src/2-2-server.py')
    
    # 1. Initialize
    init_request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}},
        "id": 1
    }
    
    # 2. List Tools
    list_tools_request = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "id": 2
    }
    
    # 3. Call Tool (Valid)
    call_valid_request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "add_numbers",
            "arguments": {"a": 5, "b": 7}
        },
        "id": 3
    }
    
    full_input = (
        json.dumps(init_request) + "\n" +
        json.dumps(list_tools_request) + "\n" +
        json.dumps(call_valid_request) + "\n"
    )
    
    print("--- Testing 2-2 Server ---")
    
    process = subprocess.Popen(
        [sys.executable, server_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    stdout, stderr = process.communicate(input=full_input, timeout=2)
    
    responses = stdout.strip().split('\n')
    
    # Check if we got responses
    if len(responses) < 3:
        print(f"❌ Expected at least 3 responses, got {len(responses)}")
        print(f"Stdout: {stdout}")
        print(f"Stderr: {stderr}")
        return

    # Check Call Tool result
    try:
        resp3 = json.loads(responses[2])
        content = resp3.get("result", {}).get("content", [])
        if len(content) > 0 and content[0].get("text") == "12":
            print("✅ tools/call (add_numbers) returned 12 (Correct)")
        else:
            print(f"❌ tools/call invalid: {content}")
    except:
        print("❌ Failed to parse response")

if __name__ == "__main__":
    test_tools()
