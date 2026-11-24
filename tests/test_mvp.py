import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import threading
import time
from unittest.mock import patch

import numpy as np
import pytest
import soxr
from PySide6.QtWidgets import QApplication

from core import Utterances, is_question, question_key
from main import MainWindow


@pytest.mark.parametrize("text", ["What is a dictionary?", "Tell me about yourself", "Explain your project"])
def test_questions(text):
    assert is_question(text)


def test_statement_and_normalization():
    assert not is_question("Thank you for joining us today.")
    assert question_key("What is Python?") == question_key("what is python.")


def test_pause_and_short_noise():
    segmenter = Utterances()
    frame = np.full(480, 1000, dtype=np.int16).tobytes()
    for _ in range(20):
        assert segmenter.feed(frame, True) is None
    for _ in range(29):
        assert segmenter.feed(bytes(960), False) is None
    result = segmenter.feed(bytes(960), False)
    assert result.dtype == np.float32
    assert len(result) == 50 * 480
    for _ in range(100):
        assert segmenter.feed(bytes(960), False) is None


@pytest.mark.parametrize("rate", [44100, 48000, 96000])
def test_resampling(rate):
    samples = np.sin(2 * np.pi * 440 * np.arange(rate) / rate).astype(np.float32)
    resampler = soxr.ResampleStream(rate, 16000, 1, dtype="float32")
    output = resampler.resample_chunk(samples, last=True)
    assert len(output) == 16000
    assert np.max(np.abs(output)) <= 1.01


def test_ui_dedup_stream_and_stop():
    app = QApplication.instance() or QApplication([])
    with patch.object(MainWindow, "background"), patch.object(MainWindow, "refresh_devices"):
        window = MainWindow(load_model=False)
    window.api_key, window.model = "fake-key", "fake-model"
    window.answer_busy = True
    window.enqueue_answer("What is a dictionary?", True)
    window.enqueue_answer("what is a dictionary.", True)
    assert len(window.pending_answers) == 1
    window.active = True
    old_session, old_answer = window.session, window.answer_id
    window.stop()
    window.events.put(("transcript", old_session, "Late transcript"))
    window.events.put(("chunk", old_answer, "Late answer"))
    window.poll()
    assert not window.transcript.toPlainText()
    assert not window.answer.toPlainText()
    assert not window.pending_answers
    window.answer_busy = False
    with patch("backend.stream_answer", side_effect=lambda k, m, q, c, emit: emit("A dictionary stores key-value pairs.")):
        window.enqueue_answer("What is a dictionary?", False)
        deadline = time.monotonic() + 2
        while window.answer_busy and time.monotonic() < deadline:
            window.poll()
            time.sleep(0.01)
    assert "key-value pairs" in window.answer.toPlainText()
    window.close()


def test_capture_stop_closes_stream():
    import backend
    import queue
    closed = threading.Event()
    class Stream:
        def __enter__(self): return self
        def __exit__(self, *args): closed.set()
        def is_active(self): return True
    device = dict(index=1, name="Test", isLoopbackDevice=True, defaultSampleRate=48000, maxInputChannels=2)
    class Audio:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def get_device_info_by_index(self, index): return device
        def open(self, **kwargs): return Stream()
    cancel, events = threading.Event(), queue.Queue()
    with patch("backend.pa.PyAudio", Audio):
        thread = threading.Thread(target=backend.capture, args=(device, 1, cancel, None, events))
        thread.start()
        assert events.get(timeout=2)[0] == "listening"
        cancel.set()
        thread.join(timeout=0.5)
        assert not thread.is_alive()
        assert closed.is_set()
