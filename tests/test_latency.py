import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import json
import time
from unittest.mock import patch

from PySide6.QtWidgets import QApplication, QSizeGrip
from main import MainWindow
from core import Utterances
from timing_metrics import record


def test_metrics_are_numeric_and_content_free(capsys):
    record("whisper", 7, 10.0, 10.125)
    assert json.loads(capsys.readouterr().out) == {"timing": "whisper", "id": 7, "ms": 125}


def test_shorter_pause_splits_hesitation():
    counts = []
    for pause in (900, 690):
        segmenter = Utterances(pause)
        count = 0
        for speech in [True] * 20 + [False] * 25 + [True] * 20 + [False] * 35:
            count += segmenter.feed(bytes(960), speech) is not None
        counts.append(count)
    assert counts == [1, 2]


def test_grip_and_first_visible_text_timing(capsys):
    app = QApplication.instance() or QApplication([])
    with patch.object(MainWindow, "background"), patch.object(MainWindow, "refresh_devices"):
        window = MainWindow(load_model=False)
    window.show()
    window.open_floating_answer()
    floating = window.floating_window
    assert isinstance(floating.size_grip, QSizeGrip)
    assert floating.size_grip.window() is floating
    assert floating.size_grip.isVisible()
    app.processEvents()
    request = window.answer_id
    window.events.put(("request_started", request, time.monotonic() - .1))
    window.events.put(("chunk", request, "private answer content"))
    window.poll()
    for _ in range(4):
        app.processEvents()
    output = capsys.readouterr().out
    assert output.count("gemini_to_visible") == 1
    assert "private" not in output
    window.events.put(("chunk", request, " more"))
    window.poll()
    for _ in range(4):
        app.processEvents()
    assert "gemini_to_visible" not in capsys.readouterr().out
    window.close()
