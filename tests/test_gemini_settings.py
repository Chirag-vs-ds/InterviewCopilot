import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from google.genai import errors, types
from PySide6.QtWidgets import QApplication, QLineEdit

import backend
from main import MainWindow, SettingsDialog


def test_models_use_capability_not_name():
    api = MagicMock()
    api.models.list.return_value = iter([
        types.Model(name="models/gemini-2.5-flash", supported_actions=["generateContent"]),
        types.Model(name="models/other-text", supported_actions=["generateContent"]),
        types.Model(name="models/embed", supported_actions=["embedContent"]),
        types.Model(name="models/unknown"),
    ])
    with patch("backend.client") as factory:
        factory.return_value.__enter__.return_value = api
        assert backend.available_models("test-placeholder") == ["models/gemini-2.5-flash", "models/other-text"]


def test_connection_is_minimal_and_preserves_selected_model():
    api = MagicMock()
    api.models.generate_content.return_value = SimpleNamespace(text="OK")
    with patch("backend.client") as factory:
        factory.return_value.__enter__.return_value = api
        assert backend.test_connection("test-placeholder", "models/gemini-2.5-flash") == "Connection successful."
    api.models.generate_content.assert_called_once_with(
        model="models/gemini-2.5-flash", contents="Reply with OK.")


@pytest.mark.parametrize("code", [400, 403, 404, 429, 503])
def test_http_errors_sanitized(code):
    secret = "test secret/with+symbols"
    from urllib.parse import quote
    exc = errors.APIError(code, {"error": {"message":
        f"Unsupported request; {secret}; {quote(secret, safe='')}; "
        "https://example.invalid/?key=hidden x-goog-api-key: hidden Bearer hidden"}})
    result = backend.api_error(exc, (secret,))
    assert f"HTTP {code}" in result
    assert "Unsupported request" in result
    assert secret not in result and quote(secret, safe="") not in result
    assert "hidden" not in result


def test_transport_error_does_not_dump_request():
    assert "private" not in backend.api_error(RuntimeError("private credential in URL"))
    assert "HTTP status unavailable" in backend.api_error(RuntimeError())


@pytest.mark.parametrize("action", ["load", "test"])
def test_dialog_errors_and_selection(action, capsys):
    app = QApplication.instance() or QApplication([])
    with patch.object(MainWindow, "background"), patch.object(MainWindow, "refresh_devices"):
        window = MainWindow(load_model=False)
    window.api_key = "placeholder-secret"
    window.models = ["models/saved", "models/gemini-2.5-flash"]
    window.model = "models/saved"
    dialog = SettingsDialog(window)
    dialog.models.setCurrentText("models/gemini-2.5-flash")
    assert dialog.key.echoMode() == QLineEdit.EchoMode.Password
    error = errors.ClientError(400, {"error": {"message": "Invalid argument placeholder-secret"}})
    target = "backend.available_models" if action == "load" else "backend.test_connection"
    with patch(target, side_effect=error) as call:
        (dialog.load_models if action == "load" else dialog.test_model)()
        deadline = time.monotonic() + 2
        while not dialog.test.isEnabled() and time.monotonic() < deadline:
            window.poll()
            app.processEvents()
            time.sleep(0.01)
        label = dialog.load_status if action == "load" else dialog.test_status
        assert "HTTP 400" in label.text()
        assert "Invalid argument" in label.text()
        assert "placeholder-secret" not in label.text()
        if action == "test":
            call.assert_called_once_with("placeholder-secret", "models/gemini-2.5-flash")
    dialog.close()
    window.close()
    captured = capsys.readouterr()
    assert "placeholder-secret" not in captured.out + captured.err
