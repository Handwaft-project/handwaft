import time
import math

start_time = time.time()

def get_fake_hand_params():
    elapsed = time.time() - start_time

    # These slowly oscillate between 0 and 1 using sine waves,
    # each at a different speed so they don't move in sync
    curl = (math.sin(elapsed * 0.5) + 1) / 2
    tilt = (math.sin(elapsed * 0.3) + 1) / 2
    spread = (math.sin(elapsed * 0.7) + 1) / 2
    height = (math.sin(elapsed * 0.4) + 1) / 2

    return curl, tilt, spread, height