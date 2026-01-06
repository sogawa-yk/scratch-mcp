import sys
import json
import subprocess
import threading
import os
import concurrent.futures
import time

# Use the new v7-1 server
SERVER_SCRIPT = os.path.join(os.path.dirname(__file__), "7-1-server.py")

class MCPClient:
    def __init__(self, server_script_path=None, notification_handler=None, sampling_callback=None):
        target_script = server_script_path if server_script_path else SERVER_SCRIPT
        
        self.notification_handler = notification_handler
        self.sampling_callback = sampling_callback

        # 1. Start Server Process
        self.process = subprocess.Popen(
            [sys.executable, target_script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=sys.stderr, # Direct stderr to parent's stderr for debugging
            text=True
        )
        self._request_id = 0
        self._lock = threading.Lock()
        self._pending_requests = {}
        
        # 2. Start Reader Thread
        self.running = True
        self.reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self.reader_thread.start()

    def _reader_loop(self):
        try:
            for line in self.process.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    
                    # 1. Response (has id, AND (result OR error)) - Logic to distinguish response from request with id
                    # In JSON-RPC 2.0, Request has 'method', Response does NOT have 'method'.
                    if "id" in data and "method" not in data:
                        request_id = data["id"]
                        if request_id in self._pending_requests:
                            future = self._pending_requests[request_id]
                            if not future.done():
                                future.set_result(data)
                        else:
                            print(f"[Warn] Received response for unknown ID: {request_id}")
                    
                    # 2. Notification (no id, has method)
                    elif "id" not in data and "method" in data:
                        if self.notification_handler:
                            self.notification_handler(data)

                    # 3. Request (has id, has method) - SERVER REQUESTING CLIENT (Sampling)
                    elif "id" in data and "method" in data:
                        threading.Thread(target=self._handle_server_request, args=(data,), daemon=True).start()
                    
                    else:
                        print(f"[Warn] Unknown message format: {data}")
                        
                except json.JSONDecodeError:
                    print(f"[Error] Failed to parse JSON: {line}")
        except Exception as e:
            if self.running:
                print(f"[Fatal] Reader loop crashed: {e}")

    def _handle_server_request(self, data):
        """Handle incoming requests from the server (e.g. Sampling)."""
        method = data.get("method")
        request_id = data.get("id")
        params = data.get("params", {})

        if method == "sampling/createMessage":
            if self.sampling_callback:
                try:
                    messages = params.get("messages", [])
                    system_prompt = params.get("systemPrompt")
                    # Execute callback to get the generated text
                    generated_text = self.sampling_callback(messages, system_prompt=system_prompt)
                    
                    # Send success response
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "role": "assistant",
                            "content": {"type": "text", "text": generated_text},
                            "model": "oci-genai-sampling",
                            "stopReason": "end_turn"
                        }
                    }
                    self._send_json(response)
                except Exception as e:
                    # Send error response
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32603,
                            "message": f"Sampling error: {str(e)}"
                        }
                    }
                    self._send_json(error_response)
            else:
                 # Callback not registered
                error_response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": "Sampling callback not implemented"
                    }
                }
                self._send_json(error_response)
        else:
             # Unknown method
            error_response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
            self._send_json(error_response)

    def _send_json(self, data):
        """Helper to send JSON to server directly."""
        try:
            json_str = json.dumps(data)
            # Use lock to prevent interleaved writes if called from multiple threads
            with self._lock:
                self.process.stdin.write(json_str + "\n")
                self.process.stdin.flush()
        except Exception as e:
            print(f"[Error] Failed to send JSON: {e}")

    def send_request(self, method, params):
        future = concurrent.futures.Future()
        request_id = None

        with self._lock:
            self._request_id += 1
            request_id = self._request_id
            self._pending_requests[request_id] = future
            
            request = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params
            }
            
            try:
                json_str = json.dumps(request)
                self.process.stdin.write(json_str + "\n")
                self.process.stdin.flush()
            except Exception as e:
                del self._pending_requests[request_id]
                raise e

        try:
            response = future.result(timeout=30) # Increased timeout for nested sampling calls
            
            if "error" in response:
                raise Exception(f"MCP Error: {response['error']}")
            
            return response["result"]
                
        finally:
            if request_id in self._pending_requests:
                del self._pending_requests[request_id]

    def send_notification(self, method, params):
        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        self._send_json(message)

    def close(self):
        self.running = False
        if self.process:
            self.process.terminate()

if __name__ == "__main__":
    # Test Stub
    def dummy_sampling(messages):
        print(f"[Client] Received Sampling Request: {messages}")
        return "Echo: " + messages[0].get("content", {}).get("text", "")

    print("Starting MCP Client (v7-1)...")
    # Note: verify that 7-1-server.py exists before running this main block directly
    client = MCPClient(SERVER_SCRIPT, sampling_callback=dummy_sampling)
    # ... (Test logic simplified for brevity, main usage is via app_oci.py)
    client.close()
