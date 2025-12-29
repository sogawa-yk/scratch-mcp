import sys
import json
import subprocess
import threading
import os
import concurrent.futures
import time

# Use the new v6-2 server
SERVER_SCRIPT = os.path.join(os.path.dirname(__file__), "6-2-server.py")

class MCPClient:
    def __init__(self, server_script_path=None, notification_handler=None):
        target_script = server_script_path if server_script_path else SERVER_SCRIPT
        
        self.notification_handler = notification_handler

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
                    # DEBUG PRINT
                    # print(f"DEBUG RECEIVE: {line}")
                    data = json.loads(line)
                    
                    # Response (has ID)
                    if "id" in data and data["id"] is not None:
                        request_id = data["id"]
                        if request_id in self._pending_requests:
                            future = self._pending_requests[request_id]
                            if not future.done():
                                future.set_result(data)
                            # DEBUG
                            # print(f"DEBUG RESPONSE: {data}")
                        else:
                            print(f"[Warn] Received response for unknown ID: {request_id}")
                    
                    # Notification (no ID) - New Logic for v6-2
                    elif "method" in data:
                        # Call handler if defined
                        if self.notification_handler:
                            self.notification_handler(data)
                    
                    else:
                        print(f"[Warn] Unknown message format: {data}")
                        
                except json.JSONDecodeError:
                    print(f"[Error] Failed to parse JSON: {line}")
        except Exception as e:
            # Handle stream closing on exit gracefully
            if self.running:
                print(f"[Fatal] Reader loop crashed: {e}")
        finally:
            pass # Thread ending

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
                # If writing fails, clean up
                del self._pending_requests[request_id]
                raise e

        # Wait for response
        try:
            response = future.result(timeout=10)
            
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
        try:
            json_str = json.dumps(message)
            self.process.stdin.write(json_str + "\n")
            self.process.stdin.flush()
        except Exception as e:
            print(f"Send Error: {e}")

    def close(self):
        self.running = False
        if self.process:
            self.process.terminate()

if __name__ == "__main__":
    def simple_notification_handler(data):
        method = data.get("method")
        params = data.get("params", {})
        if method == "notifications/message":
             level = params.get("level", "info")
             message_data = params.get("data", "")
             print(f"[Server Log: {level}] {message_data}")
        else:
             print(f"[Notification] {method}: {params}")

    print("Starting MCP Client (v6-2)...")
    client = MCPClient(SERVER_SCRIPT, notification_handler=simple_notification_handler)
    
    try:
        # 1. Initialize
        print("\n--- Sending Initialize ---")
        result = client.send_request("initialize", {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0"}
        })
        print("Initialize Result:", json.dumps(result, indent=2))
        
        # 2. Initialized Notification
        client.send_notification("notifications/initialized", {})

        # 3. Call Tool (add_numbers)
        # This should trigger a server-side notification 'notifications/message'
        print("\n--- Calling Tool 'add_numbers' ---")
        result = client.send_request("tools/call", {
            "name": "add_numbers",
            "arguments": {"a": 10, "b": 25}
        })
        print("Tool Result:", json.dumps(result, indent=2))

        # Give some time for any async notifications to arrive (though they should be before result)
        time.sleep(1)

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("\nClosing client...")
        client.close()
