import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from hand_params import get_hand_params
from smoothing import Smoother
from audio_engine import start_audio, stop_audio, send_to_audio, silence

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
smoother = Smoother(smoothing_factor=0.3)

start_audio()

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

if not cap.isOpened():
    print("Could not open webcam.")
    exit()

frame_index = 0

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
        h, w, _ = frame.shape
        for hand in result.hand_landmarks:
            params = get_hand_params(hand)
            smoothed_params = smoother.update_dict(params)
            send_to_audio(smoothed_params)
            for landmark in hand:
                x = int(landmark.x * w)
                y = int(landmark.y * h)
                cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)
    else:
        silence()

    cv2.imshow("Handwaft - Hand Tracking", frame)
    if cv2.waitKey(1) == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
stop_audio()