import sys
import json

# 1. Resource Definitions
RESOURCES = {
    "memo://welcome": {
        "uri": "memo://welcome",
        "name": "Welcome Message",
        "description": "A simple welcome note",
        "mimeType": "text/plain",
        "content": "Welcome to my scratch MCP server! This is a static resource."
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
                            "protocolVersion": "2025-11-25",
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
                    for r in RESOURCES.values():
                        resource_list.append({
                            "uri": r["uri"],
                            "name": r["name"],
                            "description": r["description"],
                            "mimeType": r["mimeType"]
                        })
                    
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
                    uri = params.get("uri")
                    
                    if uri in RESOURCES:
                        r = RESOURCES[uri]
                        response = {
                            "jsonrpc": "2.0",
                            "id": request["id"],
                            "result": {
                                "contents": [
                                    {
                                        "uri": r["uri"],
                                        "mimeType": r["mimeType"],
                                        "text": r["content"]
                                    }
                                ]
                            }
                        }
                    else:
                        # Unknown URI
                        # Returning empty contents as per simple error handling
                        response = {
                            "jsonrpc": "2.0",
                            "id": request["id"],
                            "result": {
                                "contents": [] 
                            }
                        }
                        print(f"Error: Resource not found: {uri}", file=sys.stderr)

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
