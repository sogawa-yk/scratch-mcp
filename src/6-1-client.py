import sys
import json
import subprocess
import threading
import os
import concurrent.futures

# Use the server from Step 6-1
SERVER_SCRIPT = os.path.join(os.path.dirname(__file__), "6-1-server.py")

class MCPClient:
    def __init__(self):
        # 1. Start Server Process
        self.process = subprocess.Popen(
            [sys.executable, SERVER_SCRIPT],
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
                    
                    # Response (has ID)
                    if "id" in data and data["id"] is not None:
                        request_id = data["id"]
                        if request_id in self._pending_requests:
                            future = self._pending_requests[request_id]
                            if not future.done():
                                future.set_result(data)
                        else:
                            print(f"[Warn] Received response for unknown ID: {request_id}")
                    
                    # Notification (no ID)
                    else:
                        print(f"[Notification] {data}")
                        
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
