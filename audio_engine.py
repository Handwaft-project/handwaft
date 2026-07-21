import numpy as np
import sounddevice as sd

SAMPLE_RATE = 44100

current_freq = 220.0   # Hz - controlled by tilt
current_volume = 0.0   # 0.0 to 1.0 - controlled by curl
phase = 0.0

stream = None


def _audio_callback(outdata, frames, time, status):
    global phase
    t = (np.arange(frames) + phase) / SAMPLE_RATE
    wave = np.sin(2 * np.pi * current_freq * t) * current_volume
    outdata[:, 0] = wave
    phase += frames


def start_audio():
    global stream
    stream = sd.OutputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        callback=_audio_callback
    )
    stream.start()


def stop_audio():
    if stream is not None:
        stream.stop()


def send_to_audio(params):
    """
    This is where the audio engine plugs in.
    'params' is a dict: {'curl': float, 'tilt': float, 'spread': float, 'height': float}
    Samaira: replace the logic below with your real synthesis.
    """
    global current_freq, current_volume
    current_volume = params["curl"]  # closed fist = louder
    current_freq = 200 + (params["tilt"] + 1) * 200  # tilt shifts pitch ~200-400Hz


def silence():
    global current_volume
    current_volume = 0.0