import subprocess
import sys
import os
import json

def test_tools():
    server_path = os.path.join(os.path.dirname(__file__), '../src/2-3-server.py')
    
    # 1. Initialize (Check capabilities)
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
            "arguments": {"a": 10, "b": 20}
        },
        "id": 3
    }
    
    # 4. Call Tool (Invalid Args - Missing)
    call_invalid_args_request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "add_numbers",
            "arguments": {"a": 10}
        },
        "id": 4
    }
    
    # 5. Call Tool (Unknown Tool)
    call_unknown_request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "subtract_numbers",
            "arguments": {"a": 10, "b": 5}
        },
        "id": 5
    }
    
    full_input = (
        json.dumps(init_request) + "\n" +
        json.dumps(list_tools_request) + "\n" +
        json.dumps(call_valid_request) + "\n" +
        json.dumps(call_invalid_args_request) + "\n" +
        json.dumps(call_unknown_request) + "\n"
    )
    
    print("--- Testing Basic Tools ---")
    
    process = subprocess.Popen(
        [sys.executable, server_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    stdout, stderr = process.communicate(input=full_input, timeout=2)
    
    responses = stdout.strip().split('\n')
    
    # We expect 5 responses
    if len(responses) != 5:
        print(f"❌ Expected 5 responses, got {len(responses)}")
        print(f"Stdout: {stdout}")
        print(f"Stderr: {stderr}")
        return

    # 1. Check Capabilities
    try:
        resp1 = json.loads(responses[0])
        caps = resp1.get("result", {}).get("capabilities", {})
        if "tools" in caps:
            print("✅ Capabilities include 'tools' (Correct)")
        else:
            print(f"❌ Capabilities missing 'tools': {caps}")
    except:
        print("❌ Failed to parse init response")

    # 2. Check List Tools
    try:
        resp2 = json.loads(responses[1])
        tools = resp2.get("result", {}).get("tools", [])
        if len(tools) == 1 and tools[0]["name"] == "add_numbers":
            print("✅ tools/list returned 'add_numbers' (Correct)")
        else:
            print(f"❌ tools/list invalid: {tools}")
    except:
        print("❌ Failed to parse tools list response")

    # 3. Check Call Tool (Valid)
    try:
        resp3 = json.loads(responses[2])
        content = resp3.get("result", {}).get("content", [])
        if len(content) > 0 and content[0].get("text") == "30":
            print("✅ tools/call (valid) returned 30 (Correct)")
        else:
            print(f"❌ tools/call (valid) invalid: {content}")
    except:
        print("❌ Failed to parse call valid response")

    # 4. Check Call Tool (Invalid Args)
    try:
        resp4 = json.loads(responses[3])
        is_error = resp4.get("result", {}).get("isError")
        if is_error:
            print("✅ tools/call (invalid args) returned error (Correct)")
        else:
            print(f"❌ tools/call (invalid args) missing isError: {resp4}")
    except:
        print("❌ Failed to parse call invalid args response")

    # 5. Check Call Tool (Unknown)
    try:
        resp5 = json.loads(responses[4])
        is_error = resp5.get("result", {}).get("isError")
        if is_error:
            print("✅ tools/call (unknown tool) returned error (Correct)")
        else:
            print(f"❌ tools/call (unknown tool) missing isError: {resp5}")
    except:
        print("❌ Failed to parse call unknown response")

if __name__ == "__main__":
    test_tools()
