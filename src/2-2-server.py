import os
import sys
import json

# 1. Configuration
# Resolve 'data' directory relative to this script
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data"))

# 2. Resource Definitions - Dynamic now, so no static dict needed
# But we can keep an empty one or just remove it if logic changes completely.
# For now, we will rely on DATA_DIR.

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
                                # 2. Update Capabilities
                                "resources": {}
                            },
                            "serverInfo": {
                                "name": "my-scratch-server",
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
                        
                        # Security check: Ensure file_path is within DATA_DIR
                        # We use os.path.realpath to resolve symlinks and compare with DATA_DIR
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
                         print(f"Error reading resource: {error_msg} (URI: {uri})", file=sys.stderr)
                         # Returns empty contents on error as per requirement
                         response = {
                            "jsonrpc": "2.0",
                            "id": request["id"],
                            "result": {
                                "contents": [] 
                            }
                        }
                    else:
                        response = {
                            "jsonrpc": "2.0",
                            "id": request["id"],
                            "result": {
                                "contents": [
                                    {
                                        "uri": uri,
                                        "mimeType": "text/plain",
                                        "text": content_text
                                    }
                                ]
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
