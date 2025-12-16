import subprocess
import sys
import os

def test_server_io():
    # Path to the server script
    server_path = os.path.join(os.path.dirname(__file__), '../src/server.py')
    
    # Input to send
    input_text = "Hello MCP\nTesting 123\n"
    
    # Run the server process
    process = subprocess.Popen(
        [sys.executable, server_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, # Should be empty
        stderr=subprocess.PIPE, # Should contain logs
        text=True
    )
    
    # Send input and wait for output
    stdout, stderr = process.communicate(input=input_text, timeout=2)
    
    # Verification
    print("--- Verification Results ---")
    
    # 1. Check STDOUT is empty
    if stdout == "":
        print("✅ STDOUT is empty (Correct)")
    else:
        print(f"❌ STDOUT is NOT empty: {stdout!r}")
        
    # 2. Check STDERR contains the input lines
    expected_logs = "Hello MCP\nTesting 123"
    # Note: Our server implementation prints using 'print', which adds a newline. 
    # Input: "line\n" -> Read "line" (strip) -> Print "line\n"
    if expected_logs in stderr:
        print("✅ STDERR contains logged messages (Correct)")
    else:
        print(f"❌ STDERR does NOT match expectation.\nExpected in:\n{expected_logs!r}\nGot:\n{stderr!r}")

if __name__ == "__main__":
    test_server_io()
