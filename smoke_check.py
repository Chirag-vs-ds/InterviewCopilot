"""Offscreen launch and optional short real capture check; never calls Gemini."""
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import queue
import sys
import threading
import time

from PySide6.QtWidgets import QApplication
import backend
from main import MainWindow

app = QApplication([])
window = MainWindow(load_model=False)
window.show()
deadline = time.monotonic() + 5
while not window.devices.count() and time.monotonic() < deadline:
    app.processEvents()
    time.sleep(0.02)
assert window.devices.count(), "No output devices enumerated"
print(f"Desktop launch passed; {window.devices.count()} outputs listed.", flush=True)
if "--model" in sys.argv:
    window.engine.load()
    deadline = time.monotonic() + 30
    while not window.engine.ready and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.02)
    assert window.engine.ready, window.model_status.text()
    print("Background model load passed with responsive Qt event loop.", flush=True)
if "--capture" in sys.argv:
    class Sink:
        def submit(self, *args): pass
    events, cancel = queue.Queue(), threading.Event()
    thread = threading.Thread(target=backend.capture,
        args=(window.devices.currentData(), 1, cancel, Sink(), events))
    thread.start()
    first = events.get(timeout=5)
    assert first[0] == "listening", first
    time.sleep(0.5)
    start = time.monotonic()
    cancel.set()
    thread.join(timeout=2)
    assert not thread.is_alive(), "Capture did not close promptly"
    print(f"Real native-rate capture opened/closed; Stop took {time.monotonic() - start:.3f}s.", flush=True)
window.close()
app.processEvents()
print("Desktop shutdown passed.", flush=True)
