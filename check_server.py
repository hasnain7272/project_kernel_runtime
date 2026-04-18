import subprocess
import time
import urllib.request
import urllib.error
import sys

# Start the server
server = subprocess.Popen([r'.venv\\Scripts\\python.exe', 'main.py'], 
                          stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE)

try:
    # Wait for the server to start
    for _ in range(30):  # 30 seconds timeout
        try:
            with urllib.request.urlopen('http://localhost:8089/health', timeout=1) as response:
                if response.status == 200:
                    print("Server is healthy")
                    break
        except:
            pass
        time.sleep(1)
    else:
        print("Server did not start in time")
        sys.exit(1)
finally:
    # Terminate the server
    server.terminate()
    server.wait()