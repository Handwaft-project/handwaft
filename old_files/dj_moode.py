import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import sounddevice as sd
import soundfile as sf
import numpy as np
from hand_params import get_hand_params

SONG_FILE = "song.wav"

# Load the whole song into memory as a numpy array
data, SAMPLE_RATE = sf.read(SONG_FILE, dtype='float32')
if data.ndim > 1:
    data = data.mean(axis=1)  # convert stereo to mono, simpler to work with

song_length = len(data)

# Playhead position (like a finger on a vinyl record) - a float so we can move it in fractional steps
playhead = 0.0

current_speed = 1.0      # 1.0 = normal speed
current_volume = 0.3
current_bass = 0.0       # 0.0 = no boost, 1.0 = heavy bass boost

def map_range(value, in_min, in_max, out_min, out_max):
    value = max(in_min, min(in_max, value))
    ratio = (value - in_min) / (in_max - in_min)
    return out_min + ratio * (out_max - out_min)

def simple_bass_boost(chunk, amount):
    """
    Cheap bass boost: average each sample with its neighbors to smooth out
    high frequencies, then blend that smoothed (bassier) version back in.
    """
    if amount <= 0:
        return chunk
    smoothed = np.convolve(chunk, np.ones(5) / 5, mode='same')
    return chunk * (1 - amount) + smoothed * (1 + amount)

def audio_callback(outdata, frames, time_info, status):
    global playhead

    indices = playhead + np.arange(frames) * current_speed
    indices = np.mod(indices, song_length)  # loop back to start when song ends

    # Read samples at those (possibly fractional) positions using interpolation
    chunk = np.interp(indices, np.arange(song_length), data)

    chunk = simple_bass_boost(chunk, current_bass)
    outdata[:, 0] = current_volume * chunk

    playhead = (playhead + frames * current_speed) % song_length

# Set up hand tracking
BaseOptions = python.BaseOptions
HandLandmarker = vision.HandLandmarker
HandLandmarkerOptions = vision.HandLandmarkerOptions
VisionRunningMode = vision.RunningMode

options = HandLandmarkerOptions(
    base_options=BaseOptions(model_asset_path="hand_landmarker.task"),
    running_mode=VisionRunningMode.VIDEO,
    num_hands=1
)
landmarker = HandLandmarker.create_from_options(options)

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
if not cap.isOpened():
    print("Could not open webcam.")
    exit()

stream = sd.OutputStream(channels=1, samplerate=SAMPLE_RATE, callback=audio_callback)
stream.start()

frame_index = 0
print("DJ mode running. Press 'q' in the camera window to quit.")

while True:
    success, frame = cap.read()
    if not success:
        continue
    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
    timestamp_ms = int(frame_index * (1000 / 30))
    result = landmarker.detect_for_video(mp_image, timestamp_ms)
    frame_index += 1

    if result.hand_landmarks:
        hand = result.hand_landmarks[0]
        params = get_hand_params(hand)

        current_speed = map_range(params["tilt"], -1, 1, 0.5, 1.5)
        current_volume = map_range(params["height"], 0, 1, 0.05, 0.6)
        current_bass = params["curl"]

        h, w, _ = frame.shape
        for landmark in hand:
            x = int(landmark.x * w)
            y = int(landmark.y * h)
            cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)

    cv2.imshow("Handwaft DJ Mode", frame)
    if cv2.waitKey(1) == ord('q'):
        break

stream.stop()
cap.release()
cv2.destroyAllWindows()py