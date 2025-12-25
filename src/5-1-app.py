import sys
import os
import re
import json
import time
import importlib.util

# ---------------------------------------------------------
# Import MCPClient from '4-2-client.py'
# Since the filename has hyphens, we use importlib.
# ---------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
client_module_path = os.path.join(current_dir, "4-2-client.py")

spec = importlib.util.spec_from_file_location("mcp_client_module", client_module_path)
mcp_client_module = importlib.util.module_from_spec(spec)
sys.modules["mcp_client_module"] = mcp_client_module
spec.loader.exec_module(mcp_client_module)

MCPClient = mcp_client_module.MCPClient

# ---------------------------------------------------------
# Mock LLM Function
# ---------------------------------------------------------
def mock_llm_decision(user_input):
    """
    Decides whether to use a tool based on user input.
    Returns a dictionary with decision details.
    """
    # Check for "add", "tasu", or "calculate" equivalents
    # Simple regex to find two numbers
    # Pattern: looks for something like "10 ... 20" or "10, 20" with keywords
    
    keywords = ["たす", "add", "足す", "計算", "sum", "足"]
    has_keyword = any(k in user_input for k in keywords)
    
    # Extract numbers (integers)
    numbers = re.findall(r'\d+', user_input)
    
    if has_keyword and len(numbers) >= 2:
        a = int(numbers[0])
        b = int(numbers[1])
        return {
            "use_tool": True,
            "tool_name": "add_numbers",
            "tool_args": {"a": a, "b": b}
        }
    
    return {
        "use_tool": False,
        "reply": "すみません、計算以外のことは分かりません。"
    }

# ---------------------------------------------------------
# Main Chat Loop
# ---------------------------------------------------------
def run_chat_loop():
    print("Initializing MCP Client...")
    client = MCPClient()
    
    # Run client in a separate thread so we can interact with it here? 
    # MCPClient in 4-2-client.py starts its own reader thread and subprocess.
    # However, its 'run()' method is a blocking one that does the handshake and then waits.
    # We need to manually do the handshake steps here instead of calling client.run(),
    # because client.run() contains a sample execution that we don't want to repeat exactly,
    # OR we need to modify how we use it.
    
    # 4-2-client.py's `run` method does: 
    # 1. Initialize
    # 2. Initialized NOTIFICATION
    # 3. Ping
    # 4. Tool Call (sample)
    # 5. Wait for exit
    
    # We should reproduce the handshake part but control the loop ourselves.
    # Fortunately, MCPClient methods (send_request, send_notification) are public.
    
    try:
        # --- Handshake ---
        print("[System] Sending 'initialize'...")
        init_result = client.send_request("initialize", {
            "protocolVersion": "2025-11-25", 
            "capabilities": {}, 
            "clientInfo": {"name": "mock-llm-client", "version": "1.0"}
        })
        print(f"[System] Initialize result: {init_result}")
        
        print("[System] Sending 'notifications/initialized'...")
        client.send_notification("notifications/initialized", {})
        
        print("[System] Sending 'ping'...")
        ping_result = client.send_request("ping", {})
        print(f"[System] Ping result: {ping_result}")
        print("[System] Ready! (Type 'exit' to quit)\n")
        
        # --- Chat Loop ---
        while True:
            try:
                user_input = input("User: ").strip()
            except EOFError:
                break
                
            if not user_input:
                continue
                
            if user_input.lower() == "exit":
                print("[System] Exiting chat loop.")
                break
            
            # AI "Thinking"
            decision = mock_llm_decision(user_input)
            
            if decision["use_tool"]:
                print("[AI Thought] 計算ツールが必要だと判断しました。")
                tool_name = decision["tool_name"]
                tool_args = decision["tool_args"]
                
                print(f"[System] Calling tool: {tool_name} with {tool_args}")
                try:
                    result = client.send_request("tools/call", {
                        "name": tool_name,
                        "arguments": tool_args
                    })
                    print(f"[System] Tool Output: {result}")
                    
                    if "content" in result and len(result["content"]) > 0:
                        content_text = result['content'][0]['text']
                        print(f"[AI] 計算結果は {content_text} です。")
                    else:
                        print(f"[AI] ツールは実行されましたが、結果が取得できませんでした。")
                        
                except Exception as e:
                    print(f"[AI] 実行中にエラーが発生しました: {e}")
                    
            else:
                # Normal reply
                print(f"[AI] {decision['reply']}")
                
    except KeyboardInterrupt:
        print("\n[System] Interrupted by user.")
    except Exception as e:
        print(f"[System] Unexpected error: {e}")
    finally:
        print("[System] Terminating client...")
        try:
            client.process.terminate()
            client.process.wait()
        except:
            pass
        print("[System] Goodbye.")

if __name__ == "__main__":
    run_chat_loop()
