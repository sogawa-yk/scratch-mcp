import os
import sys
import json

# 1. Configuration
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data"))

# Prompt Definitions
PROMPTS = {
    "math_tutor": {
        "name": "math_tutor",
        "description": "計算機としての振る舞いを定義するシステムプロンプト",
        "arguments": [],
        "messages": [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": (
                        "あなたは計算機です。ユーザーの要望に基づいて、最適な計算を提案してください。"
                        "出力は必ずJSONスキーマに従ってください。"
                    )
                }
            }
        ]
    }
}

class MCPServer:
    def __init__(self):
        self.running = True

    def run(self):
        try:
            for line in sys.stdin:
                msg = line.strip()
                if not msg:
                    continue
                try:
                    request = json.loads(msg)
                    self.handle_request(request)
                except json.JSONDecodeError:
                    print("Error: Invalid JSON", file=sys.stderr)
                except Exception as e:
                    print(f"Error: {e}", file=sys.stderr)
        except KeyboardInterrupt:
            pass

    def send_notification(self, method, params):
        """
        Send a JSON-RPC notification to the client.
        Notifications do not have an ID and do not expect a response.
        """
        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        sys.stdout.write(json.dumps(message) + "\n")
        sys.stdout.flush()

    def send_response(self, request_id, result=None, error=None):
        response = {
            "jsonrpc": "2.0",
            "id": request_id
        }
        if error:
            response["error"] = error
        else:
            response["result"] = result if result is not None else {}
        
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()

    def handle_request(self, request):
        method = request.get("method")
        request_id = request.get("id") # Can be None for notifications from client

        if method == "initialize":
            self.handle_initialize(request_id)
        elif method == "notifications/initialized":
            self.handle_initialized_notification()
        elif method == "ping":
            self.handle_ping(request_id)
        elif method == "resources/list":
            self.handle_resources_list(request_id)
        elif method == "resources/read":
            self.handle_resources_read(request_id, request.get("params", {}))
        elif method == "tools/list":
            self.handle_tools_list(request_id)
        elif method == "tools/call":
            self.handle_tools_call(request_id, request.get("params", {}))
        elif method == "prompts/list":
            self.handle_prompts_list(request_id)
        elif method == "prompts/get":
            self.handle_prompts_get(request_id, request.get("params", {}))
        else:
            print(f"Unknown method: {method}", file=sys.stderr)

    def handle_initialize(self, request_id):
        result = {
            "protocolVersion": "2025-11-25",
            "capabilities": {
                "resources": {},
                "tools": {},
                "prompts": {}
            },
            "serverInfo": {
                "name": "my-prompts-server",
                "version": "1.0.0"
            }
        }
        self.send_response(request_id, result=result)

    def handle_initialized_notification(self):
        print("Connection initialized successfully.", file=sys.stderr)

    def handle_ping(self, request_id):
        self.send_response(request_id, result={})

    def handle_resources_list(self, request_id):
        resource_list = []
        try:
            if os.path.exists(DATA_DIR):
                for filename in os.listdir(DATA_DIR):
                    file_path = os.path.join(DATA_DIR, filename)
                    if os.path.isfile(file_path):
                        resource_list.append({
                            "uri": f"file://{file_path}",
                            "name": filename,
                            "mimeType": "text/plain"
                        })
        except Exception as e:
            print(f"Error listing resources: {e}", file=sys.stderr)
        
        self.send_response(request_id, result={"resources": resource_list})

    def handle_resources_read(self, request_id, params):
        uri = params.get("uri", "")
        content_text = ""
        error_msg = None
        
        if uri.startswith("file://"):
            file_path = uri.replace("file://", "")
            real_path = os.path.realpath(file_path)
            if real_path.startswith(DATA_DIR):
                try:
                    with open(real_path, "r", encoding="utf-8") as f:
                        content_text = f.read()
                except FileNotFoundError:
                    error_msg = "File not found"
                except Exception as e:
                    error_msg = str(e)
            else:
                error_msg = "Access denied: Path outside data directory"
        else:
            error_msg = "Invalid URI scheme"

        if error_msg:
             print(f"Error reading resource: {error_msg}", file=sys.stderr)
             self.send_response(request_id, result={"contents": []})
        else:
             self.send_response(request_id, result={
                 "contents": [{ "uri": uri, "mimeType": "text/plain", "text": content_text }]
             })

    def handle_tools_list(self, request_id):
        result = {
            "tools": [
                {
                    "name": "add_numbers",
                    "description": "Add two numbers together",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "a": { "type": "number" },
                            "b": { "type": "number" }
                        },
                        "required": ["a", "b"]
                    }
                }
            ]
        }
        self.send_response(request_id, result=result)

    def handle_tools_call(self, request_id, params):
        name = params.get("name")
        arguments = params.get("arguments", {})
        
        if name == "add_numbers":
            # Notification: Notify client that we are about to calculate
            self.send_notification("notifications/message", {
                "level": "info",
                "data": f"Tool 'add_numbers' was called with arguments: {arguments}"
            })

            try:
                a = arguments.get("a")
                b = arguments.get("b")
                if a is None or b is None: raise ValueError("Missing arguments 'a' or 'b'")
                result = float(a) + float(b)
                self.send_response(request_id, result={
                    "content": [{ "type": "text", "text": str(result) }]
                })
            except Exception as e:
                self.send_response(request_id, result={
                    "content": [{ "type": "text", "text": f"Error: {str(e)}" }],
                    "isError": True
                })
        else:
             self.send_response(request_id, result={
                "content": [{ "type": "text", "text": f"Error: Unknown tool {name}" }],
                "isError": True
            })

    def handle_prompts_list(self, request_id):
        prompt_list = []
        for key, p in PROMPTS.items():
            prompt_list.append({
                "name": p["name"],
                "description": p["description"],
                "arguments": p.get("arguments", [])
            })
        self.send_response(request_id, result={"prompts": prompt_list})

    def handle_prompts_get(self, request_id, params):
        name = params.get("name")
        
        if name in PROMPTS:
            prompt_def = PROMPTS[name]
            self.send_response(request_id, result={"messages": prompt_def["messages"]})
        else:
            self.send_response(request_id, error={
                "code": -32602,
                "message": f"Prompt not found: {name}"
            })

if __name__ == "__main__":
    server = MCPServer()
    server.run()
