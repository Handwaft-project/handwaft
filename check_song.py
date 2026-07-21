import soundfile as sf

data, samplerate = sf.read("song.wav")
print("Sample rate:", samplerate)
print("Shape:", data.shape)
print("Duration (seconds):", len(data) / samplerate)