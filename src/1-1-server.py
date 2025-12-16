import sys

def main():
    try:
        # Loop indefinitely reading from stdin
        for line in sys.stdin:
            msg = line.strip()
            if msg:
                # Log to stderr
                print(msg, file=sys.stderr)
    except KeyboardInterrupt:
        # Allow graceful exit on Ctrl+C
        pass

if __name__ == "__main__":
    main()
