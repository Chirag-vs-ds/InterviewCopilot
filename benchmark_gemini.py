"""Two public prompts, existing saved credentials, native Qt first-paint timing.

Never prints prompts, responses, keys or error bodies. Does not save settings.
"""
import time
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
import backend
from main import MainWindow

app = QApplication([])
with patch.object(MainWindow, "background"), patch.object(MainWindow, "refresh_devices"):
    window = MainWindow(load_model=False)
try:
    key = backend.read_key()
except Exception:
    key = ""
if not key or not window.model:
    print("Gemini benchmark unavailable: no accessible saved key/model.", flush=True)
    window.close()
else:
    window.api_key = key
    window.setWindowTitle("Public-question latency benchmark")
    window.show()
    prompts = iter(("What is a dictionary in Python, and how does a hash table work?",
                    "Python mein dictionary kya hai, aur hash table kaise kaam karta hai?"))
    begun = time.monotonic()
    def advance():
        if time.monotonic() - begun > 90:
            print("Gemini benchmark timed out.", flush=True)
            window.close()
            return
        if window.answer_busy:
            return
        if window.answer_id and not window.first_text_recorded:
            print("Gemini request produced no visible text; cannot measure latency.", flush=True)
        try:
            window.enqueue_answer(next(prompts), False)
        except StopIteration:
            window.close()
    timer = QTimer()
    timer.timeout.connect(advance)
    timer.start(250)
    app.exec()
