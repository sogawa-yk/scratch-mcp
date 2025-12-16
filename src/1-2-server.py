import sys
import json

def main():
    try:
        # Loop indefinitely reading from stdin
        for line in sys.stdin:
            msg = line.strip()
            if not msg:
                continue
                
            try:
                # Attempt to parse as JSON
                data = json.loads(msg)
                # Successful parse
                print(f"Received JSON: {data}", file=sys.stderr)
            except json.JSONDecodeError:
                # Failed parse
                print("Error: Invalid JSON", file=sys.stderr)
                
    except KeyboardInterrupt:
        # Allow graceful exit on Ctrl+C
        pass

if __name__ == "__main__":
    main()
