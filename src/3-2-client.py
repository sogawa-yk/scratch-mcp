import sys
import json
import subprocess
import threading
import time
import os
import concurrent.futures

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
                    
                    # リクエストへの応答（IDがあり、かつresultまたはerrorがある）
                    if "id" in data and data["id"] is not None:
                        request_id = data["id"]
                        if request_id in self._pending_requests:
                            future = self._pending_requests[request_id]
                            if not future.done():
                                future.set_result(data)
                            # 処理済みなのでprintしない（あるいはデバッグ用に控えめに出す）
                        else:
                            print(f"[Warn] Received response for unknown ID: {request_id}")
                    
                    # 通知（IDがない）
                    else:
                        print(f"[Notification] {data}")
                        
                except json.JSONDecodeError:
                    print(f"[Error] Failed to parse JSON: {line}")
        except Exception as e:
            print(f"[Fatal] Reader loop crashed: {e}")
        finally:
            print("Reader thread halted.")

    def send_request(self, method, params):
        future = concurrent.futures.Future()
        request_id = None

        with self._lock:
            self._request_id += 1
            request_id = self._request_id
            # Futureを台帳に登録
            self._pending_requests[request_id] = future
            
            request = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params
            }
            
            json_str = json.dumps(request)
            self.process.stdin.write(json_str + "\n")
            self.process.stdin.flush()

        # レスポンス待機（同期ブロック）
        try:
            # 10秒待っても返事がなければタイムアウト例外
            response = future.result(timeout=10)
            
            # アプリケーションレベルのエラーチェック
            if "error" in response:
                raise Exception(f"MCP Error: {response['error']}")
            
            return response["result"]
                
        finally:
            # クリーンアップ：終わったら必ず辞書から消す
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

    def run(self):
        print("Starting MCP Client Handshake...")
        
        try:
            # 1. Initialize
            print("Sending 'initialize'...")
            # initializeも同期リクエストにする（結果を受け取る）
            init_result = self.send_request("initialize", {
                "protocolVersion": "2024-11-05", 
                "capabilities": {}, 
                "clientInfo": {"name": "my-client", "version": "1.0"}
            })
            print(f"[Handshake] Initialize result: {init_result}")
            
            # 2. Initialized
            print("Sending 'notifications/initialized'...")
            self.send_notification("notifications/initialized", {})
            
            # 3. Ping
            print("Sending 'ping'...")
            ping_result = self.send_request("ping", {})
            print(f"[Handshake] Ping result: {ping_result}")

            # ハンドシェイク完了を少し待つ
            time.sleep(1)

            print("\n--- Sending Tool Call Request ---")
            
            # add_numbers ツールを実行
            result = self.send_request("tools/call", {
                "name": "add_numbers",
                "arguments": {"a": 10, "b": 32}
            })
            
            # 結果の表示
            print(f"Tool Result: {result}")
            
            if "content" in result and len(result["content"]) > 0:
                print(f"Calculation: {result['content'][0]['text']}")
            
        except Exception as e:
            print(f"Client Error: {e}")

        # 終了待機
        try:
            input("\nPress Enter to exit...")
        except KeyboardInterrupt:
            pass
        finally:
            self.process.terminate()
            self.process.wait()

if __name__ == "__main__":
    client = MCPClient()
    client.run()
