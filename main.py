r"""Launch with .\.venv\Scripts\python.exe main.py."""
import queue
import sys
import threading
import time
from collections import deque

from PySide6.QtCore import QSettings, QTimer, Qt, QEvent
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QPlainTextEdit, QProgressBar,
    QPushButton, QVBoxLayout, QWidget, QSizeGrip)

import backend
from core import is_question, question_key
from timing_metrics import record
from profile_store import PROFILE_PATH, load_profile, build_answer_request
from profile_ui import ProfileDialog


class SettingsDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.setWindowTitle("Gemini settings")
        self.resize(580, 260)
        layout = QFormLayout(self)
        self.key = QLineEdit(window.api_key)
        self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.models = QComboBox()
        self.models.addItems(window.models)
        self.models.setCurrentText(window.model)
        self.status = QLabel("Load models using your key, then test and save.")
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.load_status = QLabel()
        self.test_status = QLabel()
        for label in (self.load_status, self.test_status):
            label.setWordWrap(True)
            label.setTextFormat(Qt.TextFormat.PlainText)
        self.fetch = QPushButton("Load available models")
        self.test = QPushButton("Test Connection")
        self.save = QPushButton("Save")
        layout.addRow("API key", self.key)
        layout.addRow("Model", self.models)
        layout.addRow(self.fetch)
        layout.addRow(self.load_status)
        layout.addRow(self.test)
        layout.addRow(self.test_status)
        layout.addRow(self.save)
        layout.addRow(self.status)
        self.fetch.clicked.connect(self.load_models)
        self.test.clicked.connect(self.test_model)
        self.save.clicked.connect(self.save_settings)
        self.key.textEdited.connect(lambda: self.models.clear())

    def busy(self, value):
        for control in (self.fetch, self.test, self.save, self.key, self.models):
            control.setEnabled(not value)

    def run(self, work, success, action="Save settings", label=None):
        label = label if label is not None else self.status
        self.busy(True)
        label.setText(f"{action}: working...")
        def done(result, error):
            self.busy(False)
            if error:
                label.setText(f"{action}: {error}")
            else:
                success(result)
        self.window.background(work, done, secrets=(self.key.text().strip(),))

    def load_models(self):
        key = self.key.text().strip()
        if not key:
            self.status.setText("Enter an API key first.")
            return
        selected = self.models.currentText()
        self.models.clear()
        def done(models):
            self.models.clear()
            self.models.addItems(models)
            preferred = selected if selected in models else next(
                (m for m in models if "flash" in m and "lite" not in m), None)
            if preferred:
                self.models.setCurrentText(preferred)
            self.load_status.setText(f"Load available models: succeeded; found {len(models)} models supporting generateContent.")
        self.run(lambda: backend.available_models(key), done, "Load available models", self.load_status)

    def test_model(self):
        key, model = self.key.text().strip(), self.models.currentText()
        if not key or not model:
            self.status.setText("Enter your key and load available models first.")
            return
        self.run(lambda: backend.test_connection(key, model),
                 lambda result: self.test_status.setText(f"Test Connection ({model}): {result}"),
                 f"Test Connection ({model})", self.test_status)

    def save_settings(self):
        key, model = self.key.text().strip(), self.models.currentText()
        if not key or not model:
            self.status.setText("Enter your key and load available models first.")
            return
        def done(_):
            self.window.api_key, self.window.model = key, model
            self.window.models = [self.models.itemText(i) for i in range(self.models.count())]
            self.window.settings.setValue("model", model)
            self.window.status.setText("Gemini settings saved in Windows Credential Manager.")
            self.accept()
        self.run(lambda: backend.save_key(key), done)


class FloatingAnswerWindow(QWidget):
    """A second view of the main answer document, with no separate API requests."""
    def __init__(self, window):
        super().__init__(window, Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.shutting_down = False
        self.setWindowTitle("Floating Answer · Interview Copilot")
        self.resize(560, 420)
        self.setMinimumSize(320, 200)
        layout = QVBoxLayout(self)
        self.indicator = QLabel()
        self.indicator.setTextFormat(Qt.TextFormat.PlainText)
        self.indicator.setWordWrap(True)
        layout.addWidget(self.indicator)
        self.answer = QPlainTextEdit()
        self.answer.setReadOnly(True)
        self.answer.setDocument(window.answer.document())
        layout.addWidget(self.answer, 1)
        self.stop_button = QPushButton("Stop Listening")
        self.stop_button.clicked.connect(window.stop)
        layout.addWidget(self.stop_button)
        self.size_grip = QSizeGrip(self)
        self.size_grip.setFixedSize(24, 24)
        self.size_grip.setToolTip("Drag to resize")
        self.size_grip.setStyleSheet("QSizeGrip { background: #8294b5; border-radius: 3px; }")
        layout.addWidget(self.size_grip, 0, Qt.AlignmentFlag.AlignRight)
        self.answer.viewport().installEventFilter(window)

    def closeEvent(self, event):
        if self.shutting_down:
            event.accept()
        else:
            self.hide()
            event.ignore()


class MainWindow(QMainWindow):
    def __init__(self, load_model=True, profile_path=PROFILE_PATH):
        super().__init__()
        self.profile_path = profile_path
        self.profile_error = False
        try:
            self.profile = load_profile(profile_path)
        except Exception:
            self.profile = {}
            self.profile_error = True
        self.profile_dialog = None
        self.setWindowTitle("Interview Copilot · Practice MVP")
        self.resize(900, 800)
        self.events = queue.Queue()
        self.engine = backend.Engine(self.events)
        self.settings = QSettings("InterviewCopilot", "DesktopMVP")
        self.api_key = ""
        self.model = self.settings.value("model", "")
        self.models = [self.model] if self.model else []
        self.session = 0
        self.cancel = threading.Event()
        self.capture_thread = None
        self.active = False
        self.answer_cancel = threading.Event()
        self.answer_id = 0
        self.answer_busy = False
        self.pending_answers = deque()
        self.sent = set()
        self.dialogs = []
        self.floating_window = None
        self.request_started = None
        self.first_text_pending = False
        self.first_text_recorded = False
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.addWidget(QLabel("INTERVIEW COPILOT  /  System audio practice"))
        row = QHBoxLayout()
        self.devices = QComboBox()
        self.refresh = QPushButton("Refresh outputs")
        self.start = QPushButton("Start")
        self.stop_button = QPushButton("Stop")
        settings_button = QPushButton("Settings")
        for widget in (self.devices, self.refresh, self.start, self.stop_button, settings_button):
            row.addWidget(widget)
        layout.addLayout(row)
        self.profile_button = QPushButton("Profile")
        self.profile_button.clicked.connect(self.open_profile)
        layout.addWidget(self.profile_button)
        self.indicator = QLabel("● Stopped")
        layout.addWidget(self.indicator)
        self.level = QProgressBar()
        self.level.setRange(0, 100)
        self.level.setFormat("Audio level %p%")
        layout.addWidget(self.level)
        self.model_status = QLabel("Whisper not loaded")
        self.model_status.setWordWrap(True)
        layout.addWidget(self.model_status)
        self.transcript = QPlainTextEdit()
        self.transcript.setReadOnly(True)
        self.transcript.document().setMaximumBlockCount(500)
        layout.addWidget(QLabel("Transcript · finalized after a pause"))
        layout.addWidget(self.transcript, 2)
        self.question = QPlainTextEdit()
        self.question.setMaximumHeight(95)
        layout.addWidget(QLabel("Detected question · editable"))
        layout.addWidget(self.question)
        self.generate = QPushButton("Generate Answer")
        layout.addWidget(self.generate)
        self.floating_button = QPushButton("Floating Answer")
        self.floating_button.clicked.connect(self.open_floating_answer)
        layout.addWidget(self.floating_button)
        self.answer = QPlainTextEdit()
        self.answer.setReadOnly(True)
        self.answer.viewport().installEventFilter(self)
        layout.addWidget(QLabel("Answer · streamed from Gemini"))
        layout.addWidget(self.answer, 3)
        self.status = QLabel("Raw audio stays local. Only finalized questions are sent to Gemini when configured.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        if self.profile_error:
            self.status.setText("Saved profile could not be read. Open Profile to review or clear it; no profile facts are in use.")
        self.start.clicked.connect(self.start_capture)
        self.stop_button.clicked.connect(self.stop)
        self.refresh.clicked.connect(self.refresh_devices)
        self.generate.clicked.connect(lambda: self.enqueue_answer(self.question.toPlainText(), False))
        settings_button.clicked.connect(self.open_settings)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(40)
        self.background(backend.read_key, self.key_loaded)
        self.refresh_devices()
        if load_model:
            self.engine.load()

    def eventFilter(self, watched, event):
        if (event.type() == QEvent.Type.Paint and self.first_text_pending
                and not self.first_text_recorded and self.request_started is not None):
            self.first_text_recorded = True
            request, started = self.answer_id, self.request_started
            # Run after Qt paints the first chunk (not just receipt on the worker).
            def painted():
                if request == self.answer_id:
                    record("gemini_to_visible", request, started)
            QTimer.singleShot(0, painted)
        return super().eventFilter(watched, event)

    def open_profile(self):
        if self.profile_dialog is None:
            self.profile_dialog = ProfileDialog(self)
            self.profile_dialog.finished.connect(self.profile_closed)
        self.profile_dialog.show()
        self.profile_dialog.raise_()
        self.profile_dialog.activateWindow()

    def profile_closed(self):
        # Release unsaved source text/drafts instead of retaining hidden dialogs.
        dialog, self.profile_dialog = self.profile_dialog, None
        if dialog is not None:
            dialog.deleteLater()

    def set_profile(self, facts):
        self.profile = facts
        self.answer_cancel.set()
        self.answer_id += 1
        self.first_text_pending = False
        self.answer_busy = False
        self.pending_answers.clear()
        self.sent.clear()
        self.answer.clear()
        self.status.setText("Profile updated locally. Pending answers discarded. Relevant facts are used only for personal questions.")

    def open_floating_answer(self):
        if self.floating_window is None:
            self.floating_window = FloatingAnswerWindow(self)
        self.sync_floating_status()
        self.floating_window.showNormal()
        self.floating_window.raise_()
        self.floating_window.activateWindow()

    def sync_floating_status(self):
        if self.floating_window is not None:
            self.floating_window.indicator.setText(self.indicator.text())
            self.floating_window.indicator.setStyleSheet(self.indicator.styleSheet())

    def background(self, work, done, secrets=()):
        def run():
            try:
                result, error = work(), None
            except Exception as exc:
                # Never surface the key through SDK error messages.
                result, error = None, backend.api_error(exc, secrets)
            self.events.put(("task", done, result, error))
        threading.Thread(target=run, daemon=True).start()

    def key_loaded(self, key, error):
        self.api_key = key or ""
        if error:
            self.status.setText("Could not read Windows Credential Manager. Open Settings to save your key.")

    def refresh_devices(self):
        self.refresh.setEnabled(False)
        def work():
            with backend.pa.PyAudio() as audio:
                return backend.list_devices(audio)
        def done(result, error):
            self.refresh.setEnabled(True)
            if error:
                self.status.setText("Could not enumerate outputs. Connect headphones and refresh.")
                return
            devices, default = result
            self.devices.clear()
            for device in devices:
                self.devices.addItem(device["name"] + (" [Default]" if device["index"] == default else ""), device)
                if device["index"] == default:
                    self.devices.setCurrentIndex(self.devices.count() - 1)
        self.background(work, done)

    def open_settings(self):
        dialog = SettingsDialog(self)
        self.dialogs.append(dialog)
        dialog.open()

    def start_capture(self):
        if self.capture_thread and self.capture_thread.is_alive():
            return
        if not self.engine.ready:
            self.engine.load()
            self.status.setText("Wait for Whisper to finish loading, then press Start.")
            return
        device = self.devices.currentData()
        if not device:
            self.status.setText("Select an output device first.")
            return
        self.session += 1
        self.cancel = threading.Event()
        self.active = True
        self.sent.clear()
        self.start.setEnabled(False)
        self.devices.setEnabled(False)
        self.refresh.setEnabled(False)
        self.indicator.setText("● Opening capture...")
        self.capture_thread = threading.Thread(target=backend.capture,
            args=(device, self.session, self.cancel, self.engine, self.events), daemon=True)
        self.capture_thread.start()
        self.sync_floating_status()

    def stop(self):
        self.cancel.set()
        self.active = False
        self.session += 1
        self.engine.clear()
        self.answer_cancel.set()
        self.answer_id += 1
        self.first_text_pending = False
        self.answer_busy = False
        self.pending_answers.clear()
        self.indicator.setText("● Stopping..." if self.capture_thread and self.capture_thread.is_alive() else "● Stopped")
        self.indicator.setStyleSheet("")
        self.level.setValue(0)
        self.status.setText("Stopped. Pending results discarded; partial utterance discarded.")
        self.sync_floating_status()

    def enqueue_answer(self, text, automatic):
        text = text.strip()
        key = question_key(text)
        if not text:
            self.status.setText("Enter a question first.")
            return
        if not self.api_key or not self.model:
            self.status.setText("Open Settings to configure Gemini. Your transcript remains local.")
            return
        if automatic and key in self.sent:
            return
        if len(self.pending_answers) >= 10:
            self.status.setText("Answer queue full. Use Generate Answer for the missed question.")
            return
        if automatic:
            self.sent.add(key)
        self.pending_answers.append((text, time.monotonic()))
        self.next_answer()

    def next_answer(self):
        if self.answer_busy or not self.pending_answers:
            return
        text, queued_at = self.pending_answers.popleft()
        self.answer_busy = True
        self.answer_id += 1
        request = self.answer_id
        self.request_started = None
        self.first_text_pending = self.first_text_recorded = False
        cancel = self.answer_cancel = threading.Event()
        key, model = self.api_key, self.model
        answer_request = build_answer_request(text, self.profile)
        self.answer.setPlainText(f"Question: {text}\n\n")
        self.status.setText("Generating answer...")
        def work():
            try:
                started = time.monotonic()
                record("answer_queue", request, queued_at, started)
                self.events.put(("request_started", request, started))
                backend.stream_answer(key, model, answer_request, cancel,
                    lambda chunk: self.events.put(("chunk", request, chunk)))
                self.events.put(("answer_done", request, "Answer complete."))
            except Exception as exc:
                self.events.put(("answer_done", request, backend.api_error(exc, (key,))))
        threading.Thread(target=work, daemon=True).start()

    def poll(self):
        for _ in range(200):
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            kind = event[0]
            if kind == "task":
                event[1](event[2], event[3])
            elif kind == "model":
                self.model_status.setText(event[1])
            elif kind in ("chunk", "answer_done", "request_started"):
                if event[1] != self.answer_id:
                    continue
                if kind == "request_started":
                    self.request_started = event[2]
                elif kind == "chunk":
                    if event[2].strip():
                        self.first_text_pending = True
                    self.answer.moveCursor(QTextCursor.MoveOperation.End)
                    self.answer.insertPlainText(event[2])
                else:
                    self.answer_busy = False
                    self.status.setText(event[2])
                    self.next_answer()
            elif event[1] == self.session and self.active:
                value = event[2]
                if kind == "listening":
                    self.indicator.setText(f"● LISTENING · {value}")
                    self.indicator.setStyleSheet("color: #5ee6a8")
                elif kind == "level":
                    self.level.setValue(min(100, int(value * 400)))
                elif kind == "transcript":
                    self.transcript.appendPlainText(value)
                    self.status.setText("Utterance transcribed. Listening...")
                    if is_question(value):
                        self.question.setPlainText(value)
                        self.enqueue_answer(value, True)
                elif kind == "capture_error":
                    self.stop()
                    self.status.setText(value)
                elif kind in ("error", "status"):
                    self.status.setText(value)
        if not self.active and not (self.capture_thread and self.capture_thread.is_alive()):
            self.start.setEnabled(True)
            self.devices.setEnabled(True)
            self.refresh.setEnabled(True)
            self.indicator.setText("● Stopped")

        self.sync_floating_status()

    def closeEvent(self, event):
        self.stop()
        self.timer.stop()
        if self.floating_window is not None:
            self.floating_window.shutting_down = True
            self.floating_window.close()
        self.engine.shutdown.set()
        if self.capture_thread:
            self.capture_thread.join(timeout=1)
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet("""
        QWidget { background: #171b25; color: #e8edf8; font-size: 14px; }
        QPlainTextEdit, QLineEdit, QComboBox { background: #222939; border: 1px solid #3c4860; padding: 8px; }
        QPushButton { background: #344b83; border: 0; border-radius: 5px; padding: 10px; }
        QPushButton:hover { background: #4566ae; }
        QPushButton:disabled { background: #293140; color: #7d879a; }
        QLabel { padding: 3px; }
        QProgressBar { border: 0; background: #222939; text-align: center; max-height: 18px; }
        QProgressBar::chunk { background: #397a69; }
    """)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
