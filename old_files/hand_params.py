
import numpy as np

# Landmark index reference (MediaPipe Hand model):
# 0 = wrist
# 1-4   = thumb  (CMC, MCP, IP, TIP)
# 5-8   = index  (MCP, PIP, DIP, TIP)
# 9-12  = middle (MCP, PIP, DIP, TIP)
# 13-16 = ring   (MCP, PIP, DIP, TIP)
# 17-20 = pinky  (MCP, PIP, DIP, TIP)

def to_array(landmark):
    """Convert one MediaPipe landmark into a NumPy [x, y, z] array."""
    return np.array([landmark.x, landmark.y, landmark.z])


def distance(a, b):
    """Straight-line distance between two points."""
    return np.linalg.norm(a - b)


def get_curl(landmarks):
    """
    Average curl across the 4 main fingers (index, middle, ring, pinky).
    0.0 = fully open/straight hand, 1.0 = fully closed fist.
    """
    finger_joint_groups = [
        [5, 6, 7, 8],      # index
        [9, 10, 11, 12],   # middle
        [13, 14, 15, 16],  # ring
        [17, 18, 19, 20],  # pinky
    ]
    wrist = to_array(landmarks[0])

    curls = []
    for mcp_i, pip_i, dip_i, tip_i in finger_joint_groups:
        mcp = to_array(landmarks[mcp_i])
        pip = to_array(landmarks[pip_i])
        dip = to_array(landmarks[dip_i])
        tip = to_array(landmarks[tip_i])

        # Distance if the finger were a straight line from wrist to tip
        straight_dist = distance(wrist, tip)
        # Distance following the actual finger segments (always >= straight_dist)
        path_dist = (
            distance(wrist, mcp) +
            distance(mcp, pip) +
            distance(pip, dip) +
            distance(dip, tip)
        )

        curl = 1 - (straight_dist / path_dist)
        curls.append(curl)

    return float(np.mean(curls))


def get_tilt(landmarks):
    """
    Wrist tilt left/right, based on the direction the hand is pointing.
    Roughly -1 (tilted left) to 1 (tilted right), 0 = neutral/up.
    """
    wrist = to_array(landmarks[0])
    middle_mcp = to_array(landmarks[9])

    direction = middle_mcp - wrist
    tilt = direction[0] / (np.linalg.norm(direction) + 1e-6)
    return float(tilt)


def get_spread(landmarks):
    """
    How spread apart the fingers are.
    Higher = fingers spread wide, lower = fingers held together.
    """
    tip_indices = [4, 8, 12, 16, 20]  # thumb, index, middle, ring, pinky tips
    tips = [to_array(landmarks[i]) for i in tip_indices]

    spreads = []
    for i in range(len(tips) - 1):
        spreads.append(distance(tips[i], tips[i + 1]))

    return float(np.mean(spreads))


def get_height(landmarks):
    """
    Hand height in the frame.
    0.0 = bottom of frame, 1.0 = top of frame.
    """
    wrist_y = landmarks[0].y
    return float(1 - wrist_y)


def get_hand_params(landmarks):
    """
    Main function: takes the 21 landmarks for one hand,
    returns a dictionary of the four control values.
    """
    return {
        "curl": get_curl(landmarks),
        "tilt": get_tilt(landmarks),
        "spread": get_spread(landmarks),
        "height": get_height(landmarks),
    }