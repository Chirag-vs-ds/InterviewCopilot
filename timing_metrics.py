"""Content-free monotonic stage measurements, printed to the launch terminal."""
import json
import time

STAGES = {"speech_to_finalize", "whisper", "answer_queue", "gemini_to_visible"}


def record(stage, identifier, started, ended=None):
    if stage not in STAGES or not isinstance(identifier, int):
        raise ValueError("Only fixed timing stages and numeric IDs are allowed")
    ended = time.monotonic() if ended is None else ended
    print(json.dumps({"timing": stage, "id": identifier,
                      "ms": round(max(0, ended - started) * 1000, 2)}), flush=True)
