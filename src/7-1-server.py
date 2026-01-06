import os
import sys
import json
import uuid
import subprocess

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
        # NOTE: If 'method' is missing in a response (from client), it's not a request.
        # But here server mostly receives requests, except for sampling responses (handled in request_sampling hack).
        # Actually proper async handling would separate this. 
        # For this simplified sync implementation, 'handle_request' is only for 'incoming requests' from client.
        # The 'request_sampling' method below does its own read loop for the specific response.
        
        method = request.get("method")
        
        # If no method, it might be a response to our sampling request, but 
        # in the 'request_sampling' simplified model, we catch it there.
        # If it falls through here, it might be a stray response or error.
        if not method and "id" in request:
             # Just ignore or log stray responses
            return

        if "id" in request: # IDがある場合はRequestとして扱う
            request_id = request.get("id") 

            if method == "initialize":
                self.handle_initialize(request_id)
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
                # JSON-RPC 2.0 Method Not Found
                self.send_response(request_id, error={
                    "code": -32601,
                    "message": "Method not found"
                })
        else:
            # IDがない場合はNotificationとして扱う
            if method == "notifications/initialized":
                self.handle_initialized_notification()
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
                },
                {
                    "name": "execute_shell_task",
                    "description": "Generate and execute a safe bash one-liner for a given instruction using MCP Sampling.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "instruction": { "type": "string" }
                        },
                        "required": ["instruction"]
                    }
                }
            ]
        }
        self.send_response(request_id, result=result)

    # --- Sampling Feature ---
    def request_sampling(self, prompt_text, system_prompt=None):
        """
        Send a sampling request to the client and wait for the response.
        Note: This blocks the server loop, which is fine for this tutorial but
        bad for production (needs async).
        """
        request_id = str(uuid.uuid4())
        params = {
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": prompt_text
                    }
                }
            ],
            "maxTokens": 100
        }
        if system_prompt:
            params["systemPrompt"] = system_prompt

        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "sampling/createMessage",
            "params": params
        }
        
        # Send Request
        sys.stdout.write(json.dumps(request) + "\n")
        sys.stdout.flush()
        
        # Wait for Response (Blocking)
        # We need to read from stdin until we find the response with our ID
        # WARNING: This logic steals input from the main 'run' loop.
        # Ideally we'd use a shared queue, but for simplicity here we assume 
        # this is the only activity happening during tool execution.
        try:
            while True:
                line = sys.stdin.readline()
                if not line: break
                
                try:
                    data = json.loads(line)
                    # Check if this is the response to our sampling request
                    if "id" in data and str(data["id"]) == request_id:
                        if "error" in data:
                            raise Exception(f"Sampling error: {data['error']}")
                        
                        # Extract content
                        result = data.get("result", {})
                        content = result.get("content", {})
                        if isinstance(content, dict) and content.get("type") == "text":
                            return content.get("text")
                        # Some implementations might return a list of contents
                        if isinstance(content, list) and len(content) > 0:
                             return content[0].get("text")
                             
                        return "Error: No text in content"
                    
                    # If it's NOT our response, it might be another request or notification.
                    # In a real server, we should handle or queue it. 
                    # Here, we drop it to avoid infinite recursion complexity in this demo.
                    print(f"debug: Dropped message during sampling wait: {line}", file=sys.stderr)
                    
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            return f"Error during sampling: {str(e)}"
        
        return "Error: Sampling timed out or disconnected"

    def handle_tools_call(self, request_id, params):
        name = params.get("name")
        arguments = params.get("arguments", {})
        
        if name == "add_numbers":
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

        elif name == "execute_shell_task":
            self.send_notification("notifications/message", {
                "level": "info",
                "data": f"Tool 'execute_shell_task' called."
            })
            try:
                instruction = arguments.get("instruction")
                if not instruction: raise ValueError("Missing argument 'instruction'")

                # 1. Sampling
                system_prompt = (
                    "あなたはLinuxシェルの専門家です。"
                    "以下の指示を安全に実行できるワンライナーのbashコマンドに変換してください。"
                    "解説やMarkdownは不要で、コマンド文字列のみを返してください。\n"
                    "危険なコマンド(rm -rf /等)は拒否してください。"
                )
                user_message = f"指示: {instruction}"
                
                generated_command = self.request_sampling(user_message, system_prompt)
                generated_command = generated_command.strip()

                # Safety check (simplified)
                if "Error" in generated_command:
                     raise Exception(generated_command)
                
                self.send_notification("notifications/message", {
                     "level": "info",
                     "data": f"Executing command: {generated_command}"
                })

                # 2. Execution
                exec_result = subprocess.run(
                    generated_command, 
                    shell=True, 
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )
                
                # 3. Formatter
                status = "success" if exec_result.returncode == 0 else "error"
                output = f"Stdout: {exec_result.stdout}\nStderr: {exec_result.stderr}"
                
                self.send_response(request_id, result={
                    "content": [{ "type": "text", "text": f"{status.upper()}: {output}" }]
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
