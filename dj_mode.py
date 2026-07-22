import sys
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import sounddevice as sd
import soundfile as sf
import numpy as np
from hand_params import get_hand_params

if len(sys.argv) > 1:
    SONG_FILE = sys.argv[1]
else:
    SONG_FILE = "song.wav"

data, SAMPLE_RATE = sf.read(SONG_FILE, dtype='float32')
song_length = len(data)

playhead = 0.0

current_speed = 1.0
current_volume = 0.3
current_bass = 0.0

def map_range(value, in_min, in_max, out_min, out_max):
    value = max(in_min, min(in_max, value))
    ratio = (value - in_min) / (in_max - in_min)
    return out_min + ratio * (out_max - out_min)

def simple_bass_boost(chunk, amount):
    if amount <= 0:
        return chunk
    smoothed = np.zeros_like(chunk)
    smoothed[2:-2] = (chunk[:-4] + chunk[1:-3] + chunk[2:-2] + chunk[3:-1] + chunk[4:]) / 5
    smoothed[:2] = chunk[:2]
    smoothed[-2:] = chunk[-2:]
    return chunk * (1 - amount) + smoothed * (1 + amount)

def audio_callback(outdata, frames, time_info, status):
    global playhead

    needed = int(frames * current_speed) + 4

    start = int(playhead)
    end = start + needed
    if end <= song_length:
        source_chunk = data[start:end]
    else:
        first_part = data[start:song_length]
        second_part = data[0:end - song_length]
        source_chunk = np.concatenate([first_part, second_part])

    local_positions = np.arange(len(source_chunk))
    read_positions = np.arange(frames) * current_speed
    left = np.interp(read_positions, local_positions, source_chunk[:, 0])
    right = np.interp(read_positions, local_positions, source_chunk[:, 1])

    chunk = np.stack([left, right], axis=1)
    chunk[:, 0] = simple_bass_boost(chunk[:, 0], current_bass)
    chunk[:, 1] = simple_bass_boost(chunk[:, 1], current_bass)

    outdata[:] = current_volume * chunk
    playhead = (playhead + frames * current_speed) % song_length

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

stream = sd.OutputStream(channels=2, samplerate=SAMPLE_RATE, callback=audio_callback)
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

        wrist_x = hand[0].x
        current_speed = map_range(wrist_x, 0.2, 0.8, 0.5, 1.5)

        current_volume = map_range(params["height"], 0, 1, 0.05, 0.6)

        current_bass = 1.0 if params["curl"] > 0.5 else 0.0

        h, w, _ = frame.shape
        for landmark in hand:
            x = int(landmark.x * w)
            y = int(landmark.y * h)
            cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)

        bass_label = "BASS BOOST ON" if current_bass > 0 else "bass normal"
        cv2.putText(frame, f"MOVE LEFT/RIGHT -> SPEED: {current_speed:.2f}x",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(frame, f"MOVE UP/DOWN -> VOLUME: {current_volume:.2f}",
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(frame, f"MAKE A FIST -> {bass_label}",
                    (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    else:
        cv2.putText(frame, "No hand detected", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    cv2.imshow("Handwaft DJ Mode", frame)
    if cv2.waitKey(1) == ord('q'):
        break

stream.stop()
cap.release()
cv2.destroyAllWindows()