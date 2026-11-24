"""Review imported text and explicitly confirm structured facts before saving."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton, QSplitter,
    QTabWidget, QVBoxLayout, QWidget)

from profile_store import FIELDS, save_profile, clear_profile
from resume_import import extract_resume


class ProfileDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.closed = False
        self.import_generation = 0
        self.finished.connect(self.mark_closed)
        self.setWindowTitle("Profile · Review and confirm facts")
        self.resize(960, 700)
        layout = QVBoxLayout(self)
        notice = QLabel("Import or paste locally, then copy relevant facts into the editable fields. "
                        "Only confirmed fields are saved. Relevant saved facts are sent to Gemini for personal questions.")
        notice.setWordWrap(True)
        layout.addWidget(notice)
        split = QSplitter()
        layout.addWidget(split, 1)
        source_panel = QWidget()
        source_layout = QVBoxLayout(source_panel)
        self.import_button = QPushButton("Import PDF / DOCX")
        source_layout.addWidget(self.import_button)
        source_layout.addWidget(QLabel("Source text · paste here for scanned PDFs (not saved)"))
        self.source = QPlainTextEdit()
        self.source.setPlaceholderText("Paste resume text here, or import a text-based PDF/DOCX.")
        source_layout.addWidget(self.source)
        self.destination = QComboBox()
        for field in FIELDS:
            self.destination.addItem(field.replace("_", " ").title(), field)
        source_layout.addWidget(self.destination)
        transfer = QPushButton("Copy selected source text to field")
        transfer.clicked.connect(self.transfer_selection)
        source_layout.addWidget(transfer)
        split.addWidget(source_panel)
        self.tabs = QTabWidget()
        split.addWidget(self.tabs)
        facts = QWidget()
        form = QFormLayout(facts)
        self.fields = {}
        for field in FIELDS:
            editor = QPlainTextEdit(window.profile.get(field, ""))
            editor.setMaximumHeight(105)
            form.addRow(field.replace("_", " ").title(), editor)
            self.fields[field] = editor
        self.tabs.addTab(facts, "Education and experience")
        projects_panel = QWidget()
        projects_layout = QVBoxLayout(projects_panel)
        self.projects = QTabWidget()
        projects_layout.addWidget(self.projects)
        row = QHBoxLayout()
        add, remove = QPushButton("Add Project"), QPushButton("Remove Project")
        add.clicked.connect(lambda: self.add_project())
        remove.clicked.connect(self.remove_project)
        row.addWidget(add)
        row.addWidget(remove)
        projects_layout.addLayout(row)
        self.tabs.addTab(projects_panel, "Projects")
        self.confirm = QCheckBox("I reviewed these fields and confirm they are accurate. Save only these details.")
        layout.addWidget(self.confirm)
        self.status = QLabel("Closing without Save discards edits and imported text.")
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.status)
        buttons = QHBoxLayout()
        self.save_button = QPushButton("Save Confirmed Profile")
        self.clear_button = QPushButton("Clear Profile")
        cancel = QPushButton("Cancel")
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.clear_button)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
        self.import_button.clicked.connect(self.choose_import)
        self.save_button.clicked.connect(self.save)
        self.clear_button.clicked.connect(self.clear)
        cancel.clicked.connect(self.reject)
        for editor in self.fields.values():
            editor.textChanged.connect(self.mark_dirty)
        for project in window.profile.get("projects", []):
            self.add_project(project)

    def mark_dirty(self):
        self.confirm.setChecked(False)

    def mark_closed(self):
        self.closed = True

    def add_project(self, project=None):
        project = project or {}
        if self.projects.count() >= 30:
            self.status.setText("Maximum 30 projects.")
            return
        page = QWidget()
        form = QFormLayout(page)
        page.fields = {}
        for key, label in (("name", "Project name"), ("description", "What it does"),
                           ("contribution", "What I personally built")):
            editor = QPlainTextEdit(project.get(key, ""))
            if key == "name":
                editor.setMaximumHeight(60)
            form.addRow(label, editor)
            page.fields[key] = editor
            editor.textChanged.connect(self.mark_dirty)
        index = self.projects.addTab(page, f"Project {self.projects.count() + 1}")
        self.projects.setCurrentIndex(index)
        self.mark_dirty()

    def remove_project(self):
        index = self.projects.currentIndex()
        if index >= 0:
            page = self.projects.widget(index)
            self.projects.removeTab(index)
            page.deleteLater()
            self.mark_dirty()

    def transfer_selection(self):
        text = self.source.textCursor().selectedText().replace("\u2029", "\n")
        if not text:
            self.status.setText("Select the relevant source text first, then choose its destination field.")
            return
        self.fields[self.destination.currentData()].appendPlainText(text)

    def choose_import(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import resume", "", "Resume (*.pdf *.docx)")
        if path:
            self.import_path(path)

    def import_path(self, path):
        self.import_generation += 1
        generation = self.import_generation
        self.import_button.setEnabled(False)
        self.source.setReadOnly(True)
        self.status.setText("Extracting text locally...")
        def work():
            try:
                return extract_resume(path), None
            except ValueError as exc:
                return None, str(exc)
            except Exception:
                return None, "Could not read this document. Try an unlocked PDF/DOCX or paste text instead."
        def done(result, error):
            if self.closed or generation != self.import_generation:
                return
            self.import_button.setEnabled(True)
            self.source.setReadOnly(False)
            if error:
                self.status.setText("Import failed. Paste text instead.")
                return
            text, message = result
            if message:
                self.status.setText(message)
            else:
                self.source.setPlainText(text)
                self.status.setText("Text imported locally. Review and copy facts into fields; nothing has been saved.")
        self.window.background(work, done)

    def draft(self):
        result = {key: editor.toPlainText() for key, editor in self.fields.items()}
        result["projects"] = [{key: editor.toPlainText() for key, editor in self.projects.widget(i).fields.items()}
                              for i in range(self.projects.count())]
        return result

    def save(self):
        if not self.confirm.isChecked():
            self.status.setText("Review the fields and check the confirmation box before saving.")
            return
        try:
            facts = save_profile(self.draft(), confirmed=True, path=self.window.profile_path)
        except ValueError as exc:
            self.status.setText(str(exc))
            return
        except Exception:
            self.status.setText("Could not save the profile locally. Check folder permissions.")
            return
        self.window.set_profile(facts)
        self.accept()

    def clear(self):
        try:
            clear_profile(self.window.profile_path)
        except OSError:
            self.status.setText("Could not clear the saved profile. Check folder permissions.")
            return
        self.window.set_profile({})
        self.import_generation += 1
        self.import_button.setEnabled(True)
        self.source.setReadOnly(False)
        self.source.clear()
        for field in self.fields.values():
            field.clear()
        while self.projects.count():
            self.projects.setCurrentIndex(0)
            self.remove_project()
        self.confirm.setChecked(False)
        self.status.setText("Profile cleared from this app and local storage. Imported source files are unchanged.")
