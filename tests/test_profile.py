import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import json
import time
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QApplication
from docx import Document
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

import backend
from main import MainWindow
from profile_store import save_profile, load_profile, clear_profile, build_answer_request
from profile_ui import ProfileDialog
from resume_import import extract_resume


def test_docx_import_paragraph_and_table(tmp_path):
    doc = Document()
    doc.add_paragraph("Education: B.Tech")
    doc.add_table(rows=1, cols=1).cell(0, 0).text = "Skills: Python"
    path = tmp_path / "resume.docx"
    doc.save(path)
    assert "B.Tech" in extract_resume(path)
    assert "Python" in extract_resume(path)


def make_pdf(path, text=None):
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    if text:
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"):
            DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 12 Tf 20 200 Td ({text}) Tj ET".encode())
        page[NameObject("/Contents")] = writer._add_object(stream)
    writer.write(path)


def test_pdf_import_and_scanned_fallback(tmp_path):
    path = tmp_path / "resume.pdf"
    make_pdf(path, "Education and Python skills")
    assert "Python" in extract_resume(path)
    make_pdf(path)
    with pytest.raises(ValueError, match="paste text"):
        extract_resume(path)


def test_save_reload_confirmation_and_clear(tmp_path):
    path = tmp_path / "profile.json"
    data = {"education": "B.Tech", "skills": "Python", "raw_resume": "NEVER SAVE",
            "projects": [{"name": "Planner", "description": "Plans tasks", "contribution": "Built API"}]}
    with pytest.raises(ValueError, match="Confirm"):
        save_profile(data, path=path)
    assert not path.exists()
    saved = save_profile(data, confirmed=True, path=path)
    assert load_profile(path) == saved
    assert "NEVER SAVE" not in path.read_text()
    clear_profile(path)
    assert load_profile(path) == {}
    assert not path.exists()


def test_unconfirmed_file_rejected(tmp_path):
    path = tmp_path / "profile.json"
    path.write_text(json.dumps({"version": 1, "confirmed": False, "facts": {"skills": "Private"}}))
    with pytest.raises(ValueError, match="confirmed"):
        load_profile(path)


@pytest.mark.parametrize("question", ["What is a dictionary?", "Can you explain project management?",
                                    "Explain Python", "What skills does a backend developer need?"])
def test_technical_questions_exclude_profile(question):
    assert build_answer_request(question, {"education": "PRIVATE"}) == question


def test_personal_relevance_and_missing_contribution():
    facts = {"education": "PRIVATE COLLEGE", "internships": "PRIVATE EMPLOYER", "skills": "Python",
             "projects": [{"name": "Planner", "description": "Schedules tasks", "contribution": ""},
                          {"name": "Other", "description": "UNRELATED", "contribution": "UNRELATED"}]}
    request = build_answer_request("Explain your Planner project", facts)
    assert "Schedules tasks" in request
    assert "[Add what I personally built]" in request
    assert "PRIVATE" not in request and "UNRELATED" not in request
    request = build_answer_request("Tell me about your education", facts)
    assert "PRIVATE COLLEGE" in request and "PRIVATE EMPLOYER" not in request
    request = build_answer_request("Tell me about yourself", {})
    assert "[Add confirmed education]" in request


@pytest.fixture
def window(tmp_path):
    app = QApplication.instance() or QApplication([])
    with patch.object(MainWindow, "background"), patch.object(MainWindow, "refresh_devices"):
        window = MainWindow(load_model=False, profile_path=tmp_path / "profile.json")
    yield window
    window.close()
    app.processEvents()


def test_editor_confirm_paste_cancel_and_reload(window):
    dialog = ProfileDialog(window)
    dialog.source.setPlainText("Raw private resume text")
    dialog.fields["education"].setPlainText("B.Tech")
    dialog.save()
    assert not window.profile_path.exists()
    dialog.confirm.setChecked(True)
    dialog.fields["skills"].setPlainText("Python")
    assert not dialog.confirm.isChecked()
    dialog.confirm.setChecked(True)
    dialog.save()
    assert window.profile["skills"] == "Python"
    assert "Raw private" not in window.profile_path.read_text()
    second = ProfileDialog(window)
    assert second.fields["education"].toPlainText() == "B.Tech"
    second.fields["education"].setPlainText("Unconfirmed edit")
    second.reject()
    assert load_profile(window.profile_path)["education"] == "B.Tech"
    third = ProfileDialog(window)
    third.clear()
    assert not window.profile and not window.profile_path.exists()


def test_import_preview_is_not_saved_and_scanned_message(window, tmp_path):
    dialog = ProfileDialog(window)
    doc = Document()
    doc.add_paragraph("Imported source only")
    path = tmp_path / "source.docx"
    doc.save(path)
    with patch.object(window, "background", side_effect=lambda work, done: done(work(), None)):
        dialog.import_path(path)
        assert dialog.source.toPlainText() == "Imported source only"
        assert not window.profile_path.exists()
        pdf = tmp_path / "scan.pdf"
        make_pdf(pdf)
        dialog.import_path(pdf)
        assert "paste text" in dialog.status.text()
    dialog.reject()


def test_clear_invalidates_pending_personal_answers(window):
    window.profile = {"skills": "Private"}
    old_id = window.answer_id
    window.pending_answers.append(("Tell me about yourself", time.monotonic()))
    window.set_profile({})
    window.events.put(("chunk", old_id, "Late personal answer"))
    window.poll()
    assert window.answer_cancel.is_set()
    assert not window.pending_answers and not window.answer.toPlainText()


@pytest.mark.parametrize("automatic", [False, True])
def test_same_pipeline_personal_facts_reach_sdk_and_float(window, automatic):
    window.profile = {"education": "B.Tech", "skills": "Python"}
    window.api_key, window.model = "test-placeholder", "models/test"
    window.open_floating_answer()
    api = MagicMock()
    api.models.generate_content_stream.return_value = [type("Chunk", (), {"text": "I studied B.Tech."})()]
    with patch("backend.client") as factory:
        factory.return_value.__enter__.return_value = api
        if automatic:
            window.active = True
            window.events.put(("transcript", window.session, "Tell me about yourself"))
            window.poll()
        else:
            window.question.setPlainText("Tell me about yourself")
            window.generate.click()
        deadline = time.monotonic() + 2
        while window.answer_busy and time.monotonic() < deadline:
            window.poll()
            time.sleep(.01)
    request = api.models.generate_content_stream.call_args.kwargs["contents"]
    assert "B.Tech" in request and "Python" in request
    assert window.floating_window.answer.toPlainText() == window.answer.toPlainText()
    assert "I studied B.Tech." in window.answer.toPlainText()
