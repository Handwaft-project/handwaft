import sounddevice as sd
import numpy as np

SAMPLE_RATE = 44100

current_frequency = 440
current_volume = 0.3
current_brightness = 0.0
current_spread = 0.0  # 0.0 = single note, 1.0 = full chord

def make_tone(freq, t):
    wave = np.sin(2 * np.pi * freq * t)
    wave += current_brightness * 0.5 * np.sin(2 * np.pi * freq * 2 * t)
    wave += current_brightness * 0.3 * np.sin(2 * np.pi * freq * 3 * t)
    wave += current_brightness * 0.2 * np.sin(2 * np.pi * freq * 4 * t)
    return wave / (1 + current_brightness)

def audio_callback(outdata, frames, time, status):
    t = (np.arange(frames) + audio_callback.phase) / SAMPLE_RATE

    # Base note
    wave = make_tone(current_frequency, t)

    # Extra chord notes, faded in by spread
    third = current_frequency * 1.26   # a "major third" above
    fifth = current_frequency * 1.5    # a "perfect fifth" above

    wave += current_spread * make_tone(third, t)
    wave += current_spread * make_tone(fifth, t)

    # Normalize so extra notes don't blow out the volume
    wave = wave / (1 + 2 * current_spread)

    outdata[:, 0] = current_volume * wave
    audio_callback.phase += frames

audio_callback.phase = 0

with sd.OutputStream(channels=1, samplerate=SAMPLE_RATE, callback=audio_callback):
    print("Playing. Commands: f <freq>, v <volume>, b <brightness>, s <spread>, q to quit.")
    while True:
        user_input = input("> ")
        if user_input == 'q':
            break
        parts = user_input.split()
        if len(parts) != 2:
            print("Type like: f 300  or  v 0.5  or  b 0.8  or  s 1.0")
            continue
        command, value = parts
        if command == 'f':
            current_frequency = float(value)
        elif command == 'v':
            current_volume = float(value)
        elif command == 'b':
            current_brightness = float(value)
        elif command == 's':
            current_spread = float(value)
        else:
            print("Unknown command.")