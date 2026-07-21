import sounddevice as sd
import numpy as np

SAMPLE_RATE = 44100

# This will later come from real hand tracking data.
# For now, we fake it with a variable we can change while it's playing.
current_frequency = 440

def audio_callback(outdata, frames, time, status):
    t = (np.arange(frames) + audio_callback.phase) / SAMPLE_RATE
    wave = 0.3 * np.sin(2 * np.pi * current_frequency * t)
    outdata[:, 0] = wave
    audio_callback.phase += frames

audio_callback.phase = 0

with sd.OutputStream(channels=1, samplerate=SAMPLE_RATE, callback=audio_callback):
    print("Playing... type a number and press Enter to change pitch. Type 'q' to quit.")
    while True:
        user_input = input("New frequency (Hz): ")
        if user_input == 'q':
            break
        current_frequency = float(user_input)