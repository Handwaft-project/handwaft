import sounddevice as sd
import soundfile as sf
import numpy as np

SONG_FILE = "song.wav"

data, SAMPLE_RATE = sf.read(SONG_FILE, dtype='float32')
song_length = len(data)
playhead = 0

def audio_callback(outdata, frames, time_info, status):
    global playhead
    if status:
        print(status)

    end = playhead + frames
    if end <= song_length:
        chunk = data[playhead:end]
    else:
        # wrap around to the start of the song
        first_part = data[playhead:song_length]
        second_part = data[0:end - song_length]
        chunk = np.concatenate([first_part, second_part])

    outdata[:] = 0.5 * chunk
    playhead = end % song_length

with sd.OutputStream(channels=2, samplerate=SAMPLE_RATE, callback=audio_callback):
    print("Playing plain song (direct slicing). Press Enter to stop.")
    input()