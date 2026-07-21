import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import sounddevice as sd
import numpy as np
from hand_params import get_hand_params

SAMPLE_RATE = 44100

# Shared values that the camera loop updates and the audio callback reads
current_frequency = 440
current_volume = 0.05
current_brightness = 0.0
current_spread = 0.0

def map_range(value, in_min, in_max, out_min, out_max):
    value = max(in_min, min(in_max, value))  # clamp so we don't go out of range
    ratio = (value - in_min) / (in_max - in_min)
    return out_min + ratio * (out_max - out_min)

def make_tone(freq, brightness, t):
    wave = np.sin(2 * np.pi * freq * t)
    wave += brightness * 0.5 * np.sin(2 * np.pi * freq * 2 * t)
    wave += brightness * 0.3 * np.sin(2 * np.pi * freq * 3 * t)
    wave += brightness * 0.2 * np.sin(2 * np.pi * freq * 4 * t)
    return wave / (1 + brightness)

def audio_callback(outdata, frames, time_info, status):
    t = (np.arange(frames) + audio_callback.phase) / SAMPLE_RATE
    wave = make_tone(current_frequency, current_brightness, t)

    third = current_frequency * 1.26
    fifth = current_frequency * 1.5
    wave += current_spread * make_tone(third, current_brightness, t)
    wave += current_spread * make_tone(fifth, current_brightness, t)
    wave = wave / (1 + 2 * current_spread)

    outdata[:, 0] = current_volume * wave
    audio_callback.phase += frames

audio_callback.phase = 0

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
print("Running. Press 'q' in the camera window to quit.")

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

        current_frequency = map_range(params["tilt"], -1, 1, 220, 880)
        current_volume = map_range(params["height"], 0, 1, 0.05, 0.4)
        current_brightness = params["curl"]
        current_spread = map_range(params["spread"], 0.05, 0.4, 0.0, 1.0)

        h, w, _ = frame.shape
        for landmark in hand:
            x = int(landmark.x * w)
            y = int(landmark.y * h)
            cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)

    cv2.imshow("Handwaft", frame)
    if cv2.waitKey(1) == ord('q'):
        break

stream.stop()
cap.release()
cv2.destroyAllWindows()