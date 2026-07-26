import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import sounddevice as sd
import soundfile as sf
import numpy as np
from PIL import Image
import customtkinter as ctk
from hand_params import get_hand_params

class DJScreen:
    def __init__(self, parent_frame, on_back, song_file):
        self.parent_frame = parent_frame
        self.on_back = on_back
        self.running = True

        self.data, self.SAMPLE_RATE = sf.read(song_file, dtype='float32')
        self.song_length = len(self.data)
        self.playhead = 0.0

        self.current_speed = 1.0
        self.current_volume = 0.3
        self.current_bass = 0.0

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

        self.stream = sd.OutputStream(channels=2, samplerate=self.SAMPLE_RATE,
                                        callback=self.audio_callback)
        self.stream.start()

        self.update_frame()

    def map_range(self, value, in_min, in_max, out_min, out_max):
        value = max(in_min, min(in_max, value))
        ratio = (value - in_min) / (in_max - in_min)
        return out_min + ratio * (out_max - out_min)

    def simple_bass_boost(self, chunk, amount):
        if amount <= 0:
            return chunk
        smoothed = np.zeros_like(chunk)
        smoothed[2:-2] = (chunk[:-4] + chunk[1:-3] + chunk[2:-2] + chunk[3:-1] + chunk[4:]) / 5
        smoothed[:2] = chunk[:2]
        smoothed[-2:] = chunk[-2:]
        return chunk * (1 - amount) + smoothed * (1 + amount)

    def audio_callback(self, outdata, frames, time_info, status):
        needed = int(frames * self.current_speed) + 4
        start = int(self.playhead)
        end = start + needed
        if end <= self.song_length:
            source_chunk = self.data[start:end]
        else:
            first_part = self.data[start:self.song_length]
            second_part = self.data[0:end - self.song_length]
            source_chunk = np.concatenate([first_part, second_part])

        local_positions = np.arange(len(source_chunk))
        read_positions = np.arange(frames) * self.current_speed
        left = np.interp(read_positions, local_positions, source_chunk[:, 0])
        right = np.interp(read_positions, local_positions, source_chunk[:, 1])

        chunk = np.stack([left, right], axis=1)
        chunk[:, 0] = self.simple_bass_boost(chunk[:, 0], self.current_bass)
        chunk[:, 1] = self.simple_bass_boost(chunk[:, 1], self.current_bass)

        outdata[:] = self.current_volume * chunk
        self.playhead = (self.playhead + frames * self.current_speed) % self.song_length

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

                wrist_x = hand[0].x
                self.current_speed = self.map_range(wrist_x, 0.2, 0.8, 0.5, 1.5)
                self.current_volume = self.map_range(params["height"], 0, 1, 0.05, 0.6)
                self.current_bass = 1.0 if params["curl"] > 0.5 else 0.0

                h, w, _ = frame.shape
                for landmark in hand:
                    x = int(landmark.x * w)
                    y = int(landmark.y * h)
                    cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)

                bass_label = "BASS BOOST ON" if self.current_bass > 0 else "bass normal"
                cv2.putText(frame, f"MOVE LEFT/RIGHT -> SPEED: {self.current_speed:.2f}x",
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.putText(frame, f"MOVE UP/DOWN -> VOLUME: {self.current_volume:.2f}",
                            (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.putText(frame, f"MAKE A FIST -> {bass_label}",
                            (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            else:
                cv2.putText(frame, "No hand detected", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            rgb_display = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb_display)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(640, 480))
            self.video_label.configure(image=ctk_img)
            self.video_label.image = ctk_img

        self.container.after(33, self.update_frame)

    def stop(self):
        self.running = False
        self.stream.stop()
        self.cap.release()
        self.landmarker.close()
        self.container.destroy()
        self.on_back()