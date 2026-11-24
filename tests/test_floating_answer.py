import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from unittest.mock import patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from main import MainWindow


@pytest.fixture
def window():
    app = QApplication.instance() or QApplication([])
    with patch.object(MainWindow, "background"), patch.object(MainWindow, "refresh_devices"):
        main = MainWindow(load_model=False)
    main.show()
    yield main
    main.close()
    app.processEvents()


def test_open_hide_reopen_and_shared_stream(window):
    window.answer.setPlainText("Current answer")
    window.floating_button.click()
    floating = window.floating_window
    assert floating.isVisible()
    assert floating.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
    assert floating.answer.isReadOnly()
    assert floating.answer.document() is window.answer.document()
    assert floating.answer.toPlainText() == "Current answer"
    floating.resize(650, 500)
    floating.move(100, 120)
    floating.close()
    assert not floating.isVisible()
    assert window.isVisible()
    window.events.put(("chunk", window.answer_id, " streamed while hidden"))
    window.poll()
    window.floating_button.click()
    assert window.floating_window is floating
    assert floating.isVisible()
    assert floating.width() == 650
    assert floating.answer.toPlainText() == "Current answer streamed while hidden"
    window.events.put(("chunk", window.answer_id, " and visible"))
    window.poll()
    assert floating.answer.toPlainText() == window.answer.toPlainText()
    assert floating.answer.toPlainText().endswith("and visible")
    # Starting a new answer replaces the shared content, too.
    window.answer.setPlainText("Question: next question\n\n")
    assert floating.answer.toPlainText() == window.answer.toPlainText()


def test_listening_stop_and_late_events(window):
    window.open_floating_answer()
    floating = window.floating_window
    assert floating.indicator.text() == window.indicator.text()
    window.active = True
    session, request = window.session, window.answer_id
    window.events.put(("listening", session, "Test headphones"))
    window.events.put(("chunk", request, "A streamed answer"))
    window.poll()
    assert "LISTENING" in floating.indicator.text()
    assert floating.indicator.text() == window.indicator.text()
    assert floating.indicator.styleSheet() == window.indicator.styleSheet()
    floating.stop_button.click()
    assert window.cancel.is_set() and not window.active
    assert "Stopped" in floating.indicator.text()
    window.events.put(("chunk", request, " stale"))
    window.events.put(("listening", session, "stale device"))
    window.poll()
    assert floating.answer.toPlainText() == "A streamed answer"
    assert floating.indicator.text() == window.indicator.text()
    assert "Stopped" in floating.indicator.text()


def test_main_close_closes_both(window):
    window.open_floating_answer()
    floating = window.floating_window
    window.close()
    assert not window.isVisible()
    assert not floating.isVisible()
    assert floating.shutting_down
    assert not window.timer.isActive()
