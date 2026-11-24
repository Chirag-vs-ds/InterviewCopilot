"""Native Windows grip verification harness; no audio, key or network access."""
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from main import MainWindow

app = QApplication([])
app.setStyle("Fusion")
with patch.object(MainWindow, "background"), patch.object(MainWindow, "refresh_devices"):
    window = MainWindow(load_model=False)
window.setWindowTitle("Resize verification - main")
window.answer.setPlainText("Shared answer stream verification. Drag the bottom-right grip.")
window.show()
window.open_floating_answer()
floating = window.floating_window
floating.setWindowTitle("Resize verification - floating")
floating.move(150, 150)
last = None
def report_size():
    global last
    size = (floating.width(), floating.height())
    if size != last:
        print(f"Client size: {size}; minimum: {floating.minimumWidth(), floating.minimumHeight()}", flush=True)
        last = size
timer = QTimer()
timer.timeout.connect(report_size)
timer.start(100)
app.exec()
