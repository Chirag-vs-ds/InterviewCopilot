"""Pure speech segmentation and question detection helpers."""
import re
import math
from collections import deque

import numpy as np


def question_key(text):
    return " ".join(re.findall(r"\w+", text.casefold()))


def is_question(text):
    return bool("?" in text or re.search(
        r"\b(what|why|how|when|where|who|which|explain|describe|compare|define|"
        r"implement|write|tell me|walk me|can you|could you|do you|have you)\b",
        text, re.I))


class Utterances:
    """30 ms PCM frames; 900 ms pause, 300 ms pre-roll, 25 s maximum."""
    def __init__(self, silence_ms=900):
        self.silence_frames = math.ceil(silence_ms / 30)
        self.pre = deque(maxlen=10)
        self.frames = []
        self.silence = 0
        self.voiced = 0

    def feed(self, frame, speech):
        if not self.frames:
            self.pre.append(frame)
            if not speech:
                return None
            self.frames = list(self.pre)
            self.pre.clear()
        else:
            self.frames.append(frame)
        self.voiced += int(speech)
        self.silence = 0 if speech else self.silence + 1
        if self.silence >= self.silence_frames or len(self.frames) >= 833:
            result = b"".join(self.frames) if self.voiced >= 6 else None
            self.frames = []
            self.voiced = self.silence = 0
            if result:
                return np.frombuffer(result, dtype=np.int16).astype(np.float32) / 32768
        return None
