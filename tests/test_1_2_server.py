import subprocess
import sys
import os

def test_json_parsing():
    server_path = os.path.join(os.path.dirname(__file__), '../src/1-2-server.py')
    
    # Test cases: (Input, Expected Log Fragment)
    test_cases = [
        ('{"key": "value"}', "Received JSON: {'key': 'value'}"),
        ('invalid json', "Error: Invalid JSON"),
        ('{"number": 123}', "Received JSON: {'number': 123}"),
        ('  [1, 2, 3]  ', "Received JSON: [1, 2, 3]")
    ]
    
    print("--- Testing JSON Parsing ---")
    
    process = subprocess.Popen(
        [sys.executable, server_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Send all inputs separated by newlines
    full_input = "\n".join(case[0] for case in test_cases) + "\n"
    
    stdout, stderr = process.communicate(input=full_input, timeout=2)
    
    # Verify stdout is empty
    if stdout:
        print(f"❌ STDOUT NOT EMPTY: {stdout}")
    else:
        print("✅ STDOUT is empty")
        
    # Verify logs in stderr
    all_passed = True
    for input_str, expected in test_cases:
        if expected in stderr:
            print(f"✅ Input: {input_str!r} -> Found expected log: {expected!r}")
        else:
            print(f"❌ Input: {input_str!r} -> MISSING expected log: {expected!r}")
            all_passed = False
            
    if not all_passed:
        print("\nFull STDERR:")
        print(stderr)

if __name__ == "__main__":
    test_json_parsing()
