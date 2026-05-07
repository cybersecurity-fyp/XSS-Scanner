import time
import os

# Take command from user
cmd = input("Enter XSStrike command: ")

start = time.time()

os.system(cmd)

end = time.time()

print(f"Scan time: {end - start:.2f} seconds")