import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import sounddevice as sd
import numpy as np
from PIL import Image
import customtkinter as ctk
from hand_params import get_hand_params

SAMPLE_RATE = 44100

class HandwaftScreen:
    def __init__(self, parent_frame, on_back):
        self.parent_frame = parent_frame
        self.on_back = on_back
        self.running = True

        self.current_frequency = 440
        self.current_volume = 0.05
        self.current_brightness = 0.0
        self.current_spread = 0.0
        self.phase = 0

        # UI
        self.container = ctk.CTkFrame(parent_frame, fg_color="#0a0e16")
        self.container.pack(fill="both", expand=True)

        back_btn = ctk.CTkButton(self.container, text="← Back", width=90, height=36,
                                   corner_radius=18, command=self.stop)
        back_btn.pack(anchor="w", padx=20, pady=15)

        self.video_label = ctk.CTkLabel(self.container, text="")
        self.video_label.pack(pady=10)

        # Hand tracking setup
        BaseOptions = python.BaseOptions
        HandLandmarker = vision.HandLandmarker
        HandLandmarkerOptions = vision.HandLandmarkerOptions
        VisionRunningMode = vision.RunningMode

        options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path="hand_landmarker.task"),
            running_mode=VisionRunningMode.VIDEO,
            num_hands=1
        )
        self.landmarker = HandLandmarker.create_from_options(options)

        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        self.frame_index = 0

        # Audio
        self.stream = sd.OutputStream(channels=1, samplerate=SAMPLE_RATE,
                                        callback=self.audio_callback)
        self.stream.start()

        self.update_frame()

    def map_range(self, value, in_min, in_max, out_min, out_max):
        value = max(in_min, min(in_max, value))
        ratio = (value - in_min) / (in_max - in_min)
        return out_min + ratio * (out_max - out_min)

    def make_tone(self, freq, brightness, t):
        wave = np.sin(2 * np.pi * freq * t)
        wave += brightness * 0.5 * np.sin(2 * np.pi * freq * 2 * t)
        wave += brightness * 0.3 * np.sin(2 * np.pi * freq * 3 * t)
        wave += brightness * 0.2 * np.sin(2 * np.pi * freq * 4 * t)
        return wave / (1 + brightness)

    def audio_callback(self, outdata, frames, time_info, status):
        t = (np.arange(frames) + self.phase) / SAMPLE_RATE
        wave = self.make_tone(self.current_frequency, self.current_brightness, t)
        third = self.current_frequency * 1.26
        fifth = self.current_frequency * 1.5
        wave += self.current_spread * self.make_tone(third, self.current_brightness, t)
        wave += self.current_spread * self.make_tone(fifth, self.current_brightness, t)
        wave = wave / (1 + 2 * self.current_spread)
        outdata[:, 0] = self.current_volume * wave
        self.phase += frames

    def update_frame(self):
        if not self.running:
            return

        success, frame = self.cap.read()
        if success:
            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            timestamp_ms = int(self.frame_index * (1000 / 30))
            result = self.landmarker.detect_for_video(mp_image, timestamp_ms)
            self.frame_index += 1

            if result.hand_landmarks:
                hand = result.hand_landmarks[0]
                params = get_hand_params(hand)

                self.current_frequency = self.map_range(params["tilt"], -1, 1, 220, 880)
                self.current_volume = self.map_range(params["height"], 0, 1, 0.05, 0.4)
                self.current_brightness = params["curl"]
                self.current_spread = self.map_range(params["spread"], 0.05, 0.4, 0.0, 1.0)

                h, w, _ = frame.shape
                for landmark in hand:
                    x = int(landmark.x * w)
                    y = int(landmark.y * h)
                    cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)

                cv2.putText(frame, f"PITCH: {int(self.current_frequency)}Hz",
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.putText(frame, f"VOLUME: {self.current_volume:.2f}",
                            (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.putText(frame, f"BRIGHTNESS: {self.current_brightness:.2f}",
                            (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.putText(frame, f"CHORD SPREAD: {self.current_spread:.2f}",
                            (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            else:
                cv2.putText(frame, "No hand detected", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            # Convert the OpenCV frame into something Tkinter can display
            rgb_display = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb_display)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(640, 480))
            self.video_label.configure(image=ctk_img)
            self.video_label.image = ctk_img  # keep a reference so it doesn't get garbage collected

        # Schedule the next frame update (~30fps)
        self.container.after(33, self.update_frame)

    def stop(self):
        self.running = False
        self.stream.stop()
        self.cap.release()
        self.landmarker.close()
        self.container.destroy()
        self.on_back()