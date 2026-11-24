"""Compare identical local samples; reports timings/term recall, never transcripts.

Use --english path.wav --hinglish path.wav for real recordings. Synthetic local
samples from generate_benchmark_samples.py are the default if present.
"""
import argparse
import json
import statistics
import time
from pathlib import Path

import numpy as np
import webrtcvad
from faster_whisper import WhisperModel
from faster_whisper.audio import decode_audio
from core import Utterances

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--english", default="benchmark_samples/english.wav")
parser.add_argument("--hinglish", default="benchmark_samples/hinglish.wav")
args = parser.parse_args()
results = []
model = WhisperModel("base", device="cpu", compute_type="int8", cpu_threads=4,
                     local_files_only=True, download_root=".models")
for label, path in (("english", args.english), ("hinglish", args.hinglish)):
    if not Path(path).exists():
        results.append({"sample": label, "status": "sample unavailable"})
        continue
    audio = decode_audio(path, sampling_rate=16000)
    stats = {1: [], 3: []}
    recall = {1: [], 3: []}
    # Warm up both decoders; alternate order across three measured rounds.
    for round_index, order in enumerate(((3, 1), (1, 3), (3, 1), (1, 3))):
        for beam in order:
            started = time.monotonic()
            segments, _ = model.transcribe(audio, language=None, beam_size=beam,
                                           vad_filter=True, condition_on_previous_text=False)
            text = " ".join(s.text for s in segments).casefold()
            elapsed = time.monotonic() - started
            if round_index:
                stats[beam].append(elapsed * 1000)
                recall[beam].append(sum(term in text for term in ("python", "dictionary", "hash table")))
    for beam in (3, 1):
        results.append({"sample": label, "beam": beam,
                        "median_ms": round(statistics.median(stats[beam]), 2),
                        "runs_ms": [round(v, 2) for v in stats[beam]],
                        "technical_terms_matched_out_of_3": recall[beam]})
    pcm = (np.clip(np.pad(audio, (0, 16000)), -1, .999969) * 32768).astype(np.int16).tobytes()
    for pause in (900, 690):
        vad, segmenter, count = webrtcvad.Vad(2), Utterances(pause), 0
        for i in range(0, len(pcm) - 959, 960):
            frame = pcm[i:i + 960]
            count += segmenter.feed(frame, vad.is_speech(frame, 16000)) is not None
        results.append({"sample": label, "silence_ms": pause, "utterance_count": count})

# Deterministic split stress case: a 750 ms hesitation inside one question.
for pause in (900, 690):
    segmenter, count = Utterances(pause), 0
    for speech in [True] * 20 + [False] * 25 + [True] * 20 + [False] * 35:
        count += segmenter.feed(bytes(960), speech) is not None
    results.append({"sample": "750ms_internal_pause_stress", "silence_ms": pause, "utterance_count": count})
    # Wall-clock, monotonic paced frames; excludes actual speech/VAD processing.
    segmenter = Utterances(pause)
    for _ in range(20):
        segmenter.feed(bytes(960), True)
    last_speech = time.monotonic()
    while True:
        time.sleep(.03)
        if segmenter.feed(bytes(960), False) is not None:
            break
    results.append({"sample": "paced_silence_simulation", "silence_ms": pause,
                    "finalize_ms": round((time.monotonic() - last_speech) * 1000, 2)})
Path("benchmark_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
print(json.dumps(results, indent=2))
