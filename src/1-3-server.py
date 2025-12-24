import sys
import json

def main():
    try:
        for line in sys.stdin:
            msg = line.strip()
            if not msg:
                continue
                
            try:
                request = json.loads(msg)
                
                # Basic Dispatcher
                method = request.get("method")
                
                # 1. Initialize
                if method == "initialize":
                    response = {
                        "jsonrpc": "2.0",
                        "id": request["id"],
                        "result": {
                            "protocolVersion": "2025-11-25",
                            "capabilities": {},
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
                    
                else:
                    # Unknown method (Log only)
                    print(f"Unknown method: {method}", file=sys.stderr)

            except json.JSONDecodeError:
                print("Error: Invalid JSON", file=sys.stderr)
            except Exception as e:
                # Catch other errors to keep server alive
                print(f"Error: {e}", file=sys.stderr)
                
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
