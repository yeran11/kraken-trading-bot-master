#!/usr/bin/env python3
"""Quick test to verify the server starts"""
import sys
import time
import requests
import subprocess
import threading

def test_server():
    """Test if server responds"""
    time.sleep(3)  # Wait for server to start
    try:
        response = requests.get('http://localhost:5000/api/status')
        if response.status_code == 200:
            print("✅ Server is running and responding!")
            print(f"Response: {response.json()}")
        else:
            print(f"⚠️ Server returned status code: {response.status_code}")
    except Exception as e:
        print(f"❌ Server not responding: {e}")
    finally:
        # Stop the server
        sys.exit(0)

# Start server in background
print("Starting server...")
process = subprocess.Popen([sys.executable, 'start_app.py'],
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)

# Test in separate thread
test_thread = threading.Thread(target=test_server)
test_thread.start()

# Wait for test
try:
    test_thread.join(timeout=10)
    process.terminate()
except:
    process.terminate()

print("\nTest complete!")