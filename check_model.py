"""Download/load the actual model and exercise local silent transcription."""
from pathlib import Path
import numpy as np
from faster_whisper import WhisperModel

print("Loading/downloading multilingual base, CPU int8...", flush=True)
model = WhisperModel("base", device="cpu", compute_type="int8", cpu_threads=4,
                     download_root=str(Path(__file__).resolve().parent / ".models"))
segments, info = model.transcribe(np.zeros(16000, dtype=np.float32), vad_filter=True)
assert list(segments) == []
print("Model loaded; silent transcription passed.", flush=True)
