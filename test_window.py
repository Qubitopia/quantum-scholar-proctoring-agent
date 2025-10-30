from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Set, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

import requests

from config import Endpoints


class TestWindow(QMainWindow):
    """Main Test Window showing sections, questions, and answer inputs.

    Expected question JSON shape (minimal):
    {
      "title": str,
      "sections": [
        {"title": str, "questions": [
          {"type": "mcq"|"msq"|"open-ended", "questionText": str, "options": [str, ...]?},
          ...
        ]}
      ]
    }
    """

    def __init__(self, email: str, token: str, test_id: Any, attempt_id: Any, question_json_string: str) -> None:
        super().__init__()

        # Window chrome
        self.setWindowTitle("Quantum Scholar - AI Proctored Exams (Test)")
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.showFullScreen()

        # Context
        self.email = email
        self.token = token
        self.test_id = test_id
        self.attempt_id = attempt_id

        # Parse incoming JSON safely
        try:
            question_json: Dict[str, Any] = json.loads(question_json_string)
        except Exception:
            question_json = {"title": "Test", "sections": []}

        # Model
        self.sections: List[Dict[str, Any]] = question_json.get("sections", [])
        self.test_title: str = question_json.get("title", "Test")
        self.section_titles: List[str] = [s.get("title", "Section") for s in self.sections]
        self.selected_section: int = 0
        self.selected_question: int = 0

        # Answer state storage
        # answers[(section_idx, question_idx)] =
        #   - int for mcq (1-based option index)
        #   - set[int] for msq (1-based option indices)
        #   - str for open-ended
        self.answers: Dict[int, Dict[int, Any]] = {}

        # UI references we reuse
        self.section_buttons: List[QPushButton] = []
        self.question_buttons: List[QPushButton] = []
        self.section_bar_layout: QHBoxLayout | None = None
        self.question_bar_layout: QHBoxLayout | None = None
        self.question_layout: QVBoxLayout | None = None

        # Build UI
        self._build_ui()
        self._populate_sections()
        self._populate_question_bar()
        self._update_question_display()

    # ------------------------- UI BUILDERS -------------------------
    def _build_ui(self) -> None:
        central = QWidget()
        main_layout = QVBoxLayout()

        # Top area is ~20% of screen height
        screen = QGuiApplication.primaryScreen()
        screen_height = screen.geometry().height() if screen else 800
        top_bar_height = int(screen_height * 0.20)

        top_container = QWidget()
        top_container.setFixedHeight(top_bar_height)
        top_layout = QVBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)

        # Title
        title_label = QLabel(self.test_title)
        title_label.setStyleSheet("font-size: 22px; font-weight: bold; padding: 10px;")
        top_layout.addWidget(title_label)

        # Sections bar
        section_bar_widget = QWidget()
        self.section_bar_layout = QHBoxLayout()
        section_bar_widget.setLayout(self.section_bar_layout)
        top_layout.addWidget(section_bar_widget)

        # Question numbers bar (scrollable)
        question_bar_widget = QWidget()
        self.question_bar_layout = QHBoxLayout()
        question_bar_widget.setLayout(self.question_bar_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(question_bar_widget)
        scroll.setFixedHeight(60)
        top_layout.addWidget(scroll)

        top_container.setLayout(top_layout)
        main_layout.addWidget(top_container)

        # Question display area
        self.question_area = QWidget()
        self.question_layout = QVBoxLayout()
        self.question_area.setLayout(self.question_layout)
        main_layout.addWidget(self.question_area)

        central.setLayout(main_layout)
        self.setCentralWidget(central)

    def _populate_sections(self) -> None:
        """Create/refresh section buttons with correct checked state."""
        assert self.section_bar_layout is not None

        # Clear existing
        self._clear_layout(self.section_bar_layout)
        self.section_buttons.clear()

        for idx, title in enumerate(self.section_titles):
            btn = QPushButton(title)
            btn.setCheckable(True)
            btn.setChecked(idx == self.selected_section)
            btn.clicked.connect(lambda checked, i=idx: self.select_section(i))
            self.section_bar_layout.addWidget(btn)
            self.section_buttons.append(btn)

    def _populate_question_bar(self) -> None:
        """Create/refresh question number buttons for the selected section."""
        assert self.question_bar_layout is not None

        self._clear_layout(self.question_bar_layout)
        self.question_buttons.clear()

        if not self.sections:
            return

        section_questions = self.sections[self.selected_section].get("questions", [])
        for idx, _ in enumerate(section_questions):
            btn = QPushButton(str(idx + 1))
            btn.setCheckable(True)
            btn.setChecked(idx == self.selected_question)
            btn.clicked.connect(lambda checked, i=idx: self.select_question(i))
            self.question_bar_layout.addWidget(btn)
            self.question_buttons.append(btn)

    # ---------------------------- ACTIONS ----------------------------
    def select_section(self, section_idx: int) -> None:
        """Switch to the given section and reset question index to 0."""
        self.selected_section = section_idx
        for idx, btn in enumerate(self.section_buttons):
            btn.setChecked(idx == section_idx)
        self.selected_question = 0
        self._populate_question_bar()
        self._update_question_display()

    def select_question(self, question_idx: int) -> None:
        """Switch to the given question within the current section."""
        self.selected_question = question_idx
        self._populate_question_bar()  # refresh highlighting
        self._update_question_display()

    def go_to_next_question(self) -> None:
        if not self.sections:
            return
        questions = self.sections[self.selected_section].get("questions", [])
        if self.selected_question < len(questions) - 1:
            self.selected_question += 1
            self._populate_question_bar()
            self._update_question_display()
        else:
            QMessageBox.information(self, "End of Section", "You have reached the last question in this section.")

    def save_answer(self) -> None:
        """Build the answer JSON and POST it to update-attempt endpoint."""
        payload = self._build_answer_payload()

        try:
            self.setDisabled(True)
            resp = requests.post(Endpoints.UPDATE_ATTEMPT, json=payload, timeout=15)
            if resp.ok:
                QMessageBox.information(self, "Saved", "Your answer(s) have been saved.")
            else:
                try:
                    data = resp.json()
                    msg = data.get("message") or data.get("detail") or resp.text
                except Exception:
                    msg = resp.text
                QMessageBox.warning(self, "Save Failed", f"Server returned {resp.status_code}: {msg}")
        except requests.RequestException as ex:
            QMessageBox.critical(self, "Network Error", f"Failed to save answers: {ex}")
        finally:
            self.setDisabled(False)

    # --------------------------- RENDERING ---------------------------
    def _update_question_display(self) -> None:
        assert self.question_layout is not None
        self._clear_layout(self.question_layout)

        if not self.sections:
            self.question_layout.addWidget(QLabel("No sections available."))
            return

        section = self.sections[self.selected_section]
        questions = section.get("questions", [])
        if not questions:
            self.question_layout.addWidget(QLabel("No questions in this section."))
            return

        q = questions[self.selected_question]

        # Question text
        q_label = QLabel(q.get("questionText", ""))
        q_label.setStyleSheet("font-size: 24px; padding: 8px;")
        q_label.setAlignment(Qt.AlignTop)
        self.question_layout.addWidget(q_label)

        q_type = q.get("type")
        options = q.get("options", [])

        if q_type == "mcq":
            # Single choice: radio buttons
            group = QButtonGroup(self)
            selected_idx = self._get_mcq_answer(self.selected_section, self.selected_question)
            for idx, opt in enumerate(options):
                radio = QRadioButton(str(opt))
                radio.setStyleSheet("font-size: 18px; padding: 4px;")
                radio.setChecked(selected_idx == (idx + 1))
                radio.toggled.connect(
                    lambda checked, i=idx: self._on_mcq_toggled(self.selected_section, self.selected_question, i + 1, checked)
                )
                self.question_layout.addWidget(radio)
                group.addButton(radio)
        elif q_type == "msq":
            # Multiple choice: checkboxes
            selected_set = self._get_msq_answer(self.selected_section, self.selected_question)
            for idx, opt in enumerate(options):
                cb = QCheckBox(str(opt))
                cb.setStyleSheet("font-size: 18px; padding: 4px;")
                cb.setChecked((idx + 1) in selected_set)
                cb.stateChanged.connect(
                    lambda state, i=idx: self._on_msq_changed(self.selected_section, self.selected_question, i + 1, state == Qt.Checked)
                )
                self.question_layout.addWidget(cb)
        elif q_type == "open-ended":
            # Free text
            existing = self._get_open_answer(self.selected_section, self.selected_question)
            line_edit = QLineEdit()
            line_edit.setPlaceholderText("Type your answer here...")
            if existing is not None:
                line_edit.setText(existing)
            line_edit.textChanged.connect(
                lambda text: self._set_open_answer(self.selected_section, self.selected_question, text)
            )
            self.question_layout.addWidget(line_edit)
        else:
            self.question_layout.addWidget(QLabel("Unknown question type."))

        # Actions
        buttons_row = QWidget()
        row_layout = QHBoxLayout()
        row_layout.setAlignment(Qt.AlignCenter)

        save_button = QPushButton("Save")
        next_button = QPushButton("Next")
        save_button.clicked.connect(self.save_answer)
        next_button.clicked.connect(self.go_to_next_question)

        row_layout.addWidget(save_button)
        row_layout.addWidget(next_button)
        buttons_row.setLayout(row_layout)
        self.question_layout.addWidget(buttons_row)

    # ---------------------------- HELPERS ----------------------------
    @staticmethod
    def _clear_layout(layout: QHBoxLayout | QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)

    # ---------------------------- ANSWERS ----------------------------
    def _on_mcq_toggled(self, section_idx: int, question_idx: int, option_1based: int, checked: bool) -> None:
        if checked:
            self.answers.setdefault(section_idx, {})[question_idx] = option_1based

    def _on_msq_changed(self, section_idx: int, question_idx: int, option_1based: int, checked: bool) -> None:
        section_map: Dict[int, Any] = self.answers.setdefault(section_idx, {})
        current: Set[int] = section_map.get(question_idx)
        if not isinstance(current, set):
            current = set()
        if checked:
            current.add(option_1based)
        else:
            current.discard(option_1based)
        section_map[question_idx] = current

    def _set_open_answer(self, section_idx: int, question_idx: int, text: str) -> None:
        self.answers.setdefault(section_idx, {})[question_idx] = text

    def _get_mcq_answer(self, section_idx: int, question_idx: int) -> Optional[int]:
        val = self.answers.get(section_idx, {}).get(question_idx)
        return int(val) if isinstance(val, int) else None

    def _get_msq_answer(self, section_idx: int, question_idx: int) -> Set[int]:
        val = self.answers.get(section_idx, {}).get(question_idx)
        return set(val) if isinstance(val, set) else set()

    def _get_open_answer(self, section_idx: int, question_idx: int) -> Optional[str]:
        val = self.answers.get(section_idx, {}).get(question_idx)
        return str(val) if isinstance(val, str) else None

    def _build_answer_payload(self) -> Dict[str, Any]:
        """Build payload matching sample answer_request.json format."""
        sections_payload: List[Dict[str, Any]] = []

        for s_idx, section in enumerate(self.sections):
            questions = section.get("questions", [])
            answers_list: List[Dict[str, Any]] = []
            section_answers = self.answers.get(s_idx, {})

            for q_idx, q in enumerate(questions):
                q_type = q.get("type")
                stored = section_answers.get(q_idx)
                if stored is None:
                    continue

                q_number = q_idx + 1  # 1-based
                if q_type == "mcq" and isinstance(stored, int):
                    answers_list.append({
                        "questionNumber": q_number,
                        "CorrectOption": stored,
                    })
                elif q_type == "msq" and isinstance(stored, set) and stored:
                    answers_list.append({
                        "questionNumber": q_number,
                        "CorrectOptions": sorted(list(stored)),
                    })
                elif q_type == "open-ended" and isinstance(stored, str) and stored.strip() != "":
                    answers_list.append({
                        "questionNumber": q_number,
                        "answer": stored,
                    })

            if answers_list:
                sections_payload.append({
                    "sectionId": s_idx + 1,  # 1-based
                    "answers": answers_list,
                })

        return {
            "email": self.email,
            "token": self.token,
            "attempt_id": self.attempt_id,
            "answer": {"sections": sections_payload},
        }