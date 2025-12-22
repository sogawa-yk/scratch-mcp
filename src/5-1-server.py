import os
import sys
import json

# 1. Configuration
# Resolve 'data' directory relative to this script
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data"))

# 1-1. Prompt Definitions
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

def main():
    try:
        for line in sys.stdin:
            msg = line.strip()
            if not msg:
                continue
                
            try:
                request = json.loads(msg)
                method = request.get("method")
                
                # 1. Initialize
                if method == "initialize":
                    response = {
                        "jsonrpc": "2.0",
                        "id": request["id"],
                        "result": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {
                                "resources": {},
                                "tools": {},
                                "prompts": {} # Add prompts capability
                            },
                            "serverInfo": {
                                "name": "my-prompts-server",
                                "version": "1.0.0"
                            }
                        }
                    }
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()
                
                # 2. Notification: initialized
                elif method == "notifications/initialized":
                    print("Connection initialized successfully.", file=sys.stderr)
                    
                # 3. Ping
                elif method == "ping":
                    response = {
                        "jsonrpc": "2.0",
                        "id": request["id"],
                        "result": {}
                    }
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()

                # 4. Resources List
                elif method == "resources/list":
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
                    
                    response = {
                        "jsonrpc": "2.0",
                        "id": request["id"],
                        "result": {
                            "resources": resource_list
                        }
                    }
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()

                # 5. Resources Read
                elif method == "resources/read":
                    params = request.get("params", {})
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
                         response = {
                            "jsonrpc": "2.0", "id": request["id"],
                            "result": { "contents": [] }
                        }
                    else:
                        response = {
                            "jsonrpc": "2.0", "id": request["id"],
                            "result": {
                                "contents": [{ "uri": uri, "mimeType": "text/plain", "text": content_text }]
                            }
                        }
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()

                # 6. Tools List
                elif method == "tools/list":
                    response = {
                        "jsonrpc": "2.0",
                        "id": request["id"],
                        "result": {
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
                    }
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()

                # 7. Tools Call
                elif method == "tools/call":
                    params = request.get("params", {})
                    name = params.get("name")
                    arguments = params.get("arguments", {})
                    
                    if name == "add_numbers":
                        try:
                            a = arguments.get("a")
                            b = arguments.get("b")
                            if a is None or b is None: raise ValueError("Missing arguments 'a' or 'b'")
                            result = float(a) + float(b)
                            response = {
                                "jsonrpc": "2.0", "id": request["id"],
                                "result": { "content": [{ "type": "text", "text": str(result) }] }
                            }
                        except Exception as e:
                            response = {
                                "jsonrpc": "2.0", "id": request["id"],
                                "result": { "content": [{ "type": "text", "text": f"Error: {str(e)}" }], "isError": True }
                            }
                    else:
                        response = {
                            "jsonrpc": "2.0", "id": request["id"],
                            "result": { "content": [{ "type": "text", "text": f"Error: Unknown tool {name}" }], "isError": True }
                        }
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()

                # -------------------------------------------------------------------------------------
                # 8. Prompts Features (New in Step 5-1)
                # -------------------------------------------------------------------------------------
                
                # Prompts List
                elif method == "prompts/list":
                    prompt_list = []
                    for key, p in PROMPTS.items():
                        prompt_list.append({
                            "name": p["name"],
                            "description": p["description"],
                            "arguments": p.get("arguments", [])
                        })
                    
                    response = {
                        "jsonrpc": "2.0",
                        "id": request["id"],
                        "result": {
                            "prompts": prompt_list
                        }
                    }
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()

                # Prompts Get
                elif method == "prompts/get":
                    params = request.get("params", {})
                    name = params.get("name")
                    
                    if name in PROMPTS:
                        prompt_def = PROMPTS[name]
                        response = {
                            "jsonrpc": "2.0",
                            "id": request["id"],
                            "result": {
                                "messages": prompt_def["messages"]
                            }
                        }
                    else:
                        # Error if prompt not found is not explicitly defined in spec as JSON-RPC error or app error,
                        # but standard behavior is to error.
                        response = {
                            "jsonrpc": "2.0",
                            "id": request["id"],
                            "error": {
                                "code": -32602,
                                "message": f"Prompt not found: {name}"
                            }
                        }
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()

                else:
                     print(f"Unknown method: {method}", file=sys.stderr)
            
            except json.JSONDecodeError:
                print("Error: Invalid JSON", file=sys.stderr)
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)
                
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
