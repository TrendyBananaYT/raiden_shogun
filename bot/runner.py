import os
import sys
import time
import logging

while True:    
    exit_code = os.system("python3 bot/main.py")
    print(f"main.py exited with code {exit_code}")
    
    if exit_code == 0:
        # main.py asked for a clean shutdown
        print("Shutting down runner.")
        break
    else:
        # main.py crashed or requested restart
        print("Restarting main.py...")
        time.sleep(2)
