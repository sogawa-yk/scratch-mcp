import subprocess
import sys
import os
import json

def test_prompts_server():
    server_path = os.path.join(os.path.dirname(__file__), '../src/6-1-server.py')
    
    # 1. Initialize 
    init_request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}},
        "id": 1
    }
    
    # 2. List Prompts
    list_prompts_request = {
        "jsonrpc": "2.0",
        "method": "prompts/list",
        "id": 2
    }
    
    # 3. Get Prompt (math_tutor)
    get_prompt_request = {
        "jsonrpc": "2.0",
        "method": "prompts/get",
        "params": {"name": "math_tutor"},
        "id": 3
    }
    
    full_input = (
        json.dumps(init_request) + "\n" +
        json.dumps(list_prompts_request) + "\n" +
        json.dumps(get_prompt_request) + "\n"
    )
    
    print("--- Testing 6-1 Server (Prompts) ---")
    
    process = subprocess.Popen(
        [sys.executable, server_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    stdout, stderr = process.communicate(input=full_input, timeout=2)
    
    responses = stdout.strip().split('\n')
    
    if len(responses) < 3:
        print(f"❌ Expected at least 3 responses, got {len(responses)}")
        return

    # Check Prompts Capability
    try:
        resp1 = json.loads(responses[0])
        caps = resp1.get("result", {}).get("capabilities", {})
        if "prompts" in caps:
            print("✅ Capabilities include 'prompts' (Correct)")
        else:
            print(f"❌ Capabilities missing 'prompts': {caps}")
    except:
        print("❌ Failed to parse init response")

    # Check List Prompts
    try:
        resp2 = json.loads(responses[1])
        prompts = resp2.get("result", {}).get("prompts", [])
        if any(p["name"] == "math_tutor" for p in prompts):
            print("✅ prompts/list contained 'math_tutor' (Correct)")
        else:
            print(f"❌ prompts/list missing 'math_tutor': {prompts}")
    except:
        print("❌ Failed to parse list prompts response")

    # Check Get Prompt
    try:
        resp3 = json.loads(responses[2])
        messages = resp3.get("result", {}).get("messages", [])
        if len(messages) > 0 and "計算機" in messages[0].get("content", {}).get("text", ""):
            print("✅ prompts/get returned correct content (Correct)")
        else:
            print(f"❌ prompts/get invalid: {messages}")
    except:
        print("❌ Failed to parse get prompt response")

if __name__ == "__main__":
    test_prompts_server()
