import sys
import json
import subprocess
import threading
import time
import os

# Use the server from Step 2-3
SERVER_SCRIPT = os.path.join(os.path.dirname(__file__), "2-3-server.py")

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
                    print(f"[RECV] {data}")
                except json.JSONDecodeError:
                    print(f"[RECV RAW] {line}")
        except Exception as e:
            print(f"Reader Error: {e}")
        finally:
            print("Reader thread halted.")

    def send_request(self, method, params):
        with self._lock:
            self._request_id += 1
            request_id = self._request_id
            
        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": request_id
        }
        self._send_json(message)
        return request_id

    def send_notification(self, method, params):
        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        self._send_json(message)

    def _send_json(self, message):
        try:
            json_str = json.dumps(message)
            self.process.stdin.write(json_str + "\n")
            self.process.stdin.flush()
        except Exception as e:
            print(f"Send Error: {e}")

    def run(self):
        print("Starting MCP Client Handshake...")
        
        # 1. Initialize
        print("Sending 'initialize'...")
        self.send_request("initialize", {
            "protocolVersion": "2024-11-05", 
            "capabilities": {}, 
            "clientInfo": {"name": "my-client", "version": "1.0"}
        })
        
        # Wait a bit for response (Basic implementation for Step 3-1)
        time.sleep(1)
        
        # 2. Initialized
        print("Sending 'notifications/initialized'...")
        self.send_notification("notifications/initialized", {})
        
        # 3. Ping
        print("Sending 'ping'...")
        self.send_request("ping", {})

        # 4. Wait for user exit
        try:
            input("Press Enter to exit...\n")
        except KeyboardInterrupt:
            pass
        finally:
            self.process.terminate()
            self.process.wait()

if __name__ == "__main__":
    client = MCPClient()
    client.run()
