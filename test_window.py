from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Set, Tuple

import time

from PySide6.QtCore import Qt, QTimer, QCoreApplication
from PySide6.QtGui import QGuiApplication, QKeyEvent
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

    def __init__(self, email: str, token: str, test_id: Any, attempt_id: Any, question_json_string: str, duration_minutes: int) -> None:
        super().__init__()

        # Window chrome
        self.setWindowTitle("Quantum Scholar - AI Proctored Exams (Test)")
        # Kiosk-like window behavior: frameless, full-screen, and always on top
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.showFullScreen()

        # Context
        self.email = email
        self.token = token
        self.test_id = test_id
        self.attempt_id = attempt_id
        # Countdown duration
        self.remaining_seconds: int = max(0, int(duration_minutes)) * 60

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
        self.timer_label = None  # type: Optional[QLabel]
        self.warning_label = None  # type: Optional[QLabel]
        self._countdown_timer = None  # type: Optional[QTimer]
        self._ending = False

        # Kiosk/violation state
        self.violation_count: int = 0
        self.violation_limit: int = 3
        self._last_violation_ts: float = 0.0

        # Build UI
        self._build_ui()
        self._populate_sections()
        self._populate_question_bar()
        self._update_question_display()
        self._init_countdown_timer()

        # Grab keyboard to ensure we receive as many key events as possible
        self.grabKeyboard()

        # Detect app focus changes (e.g., Alt+Tab / Win key). We can't block them at OS level
        # without elevated hooks, but we can detect and respond.
        app = QGuiApplication.instance()
        if app is not None:
            app.applicationStateChanged.connect(self._on_app_state_changed)

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

        # Title + Timer row
        header_widget = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel(self.test_title)
        title_label.setStyleSheet("font-size: 22px; font-weight: bold; padding: 10px;")

        self.timer_label = QLabel(self._format_seconds(self.remaining_seconds))
        self.timer_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.timer_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")

        # Warning banner (hidden by default)
        self.warning_label = QLabel("")
        self.warning_label.setVisible(False)
        self.warning_label.setStyleSheet(
            "background-color: #d32f2f; color: white; font-size: 14px;"
            " padding: 6px 10px; border-radius: 4px;"
        )

        end_button = QPushButton("End Test")
        end_button.setStyleSheet(
            """
            QPushButton {
                background-color: #d32f2f; color: white; padding: 6px 12px;
                font-weight: bold; border: none; border-radius: 4px;
            }
            QPushButton:hover { background-color: #b71c1c; }
            """
        )
        end_button.clicked.connect(self.end_test)

        header_layout.addWidget(title_label)
        header_layout.addStretch(1)
        header_layout.addWidget(self.timer_label)
        header_layout.addSpacing(8)
        header_layout.addWidget(self.warning_label)
        header_layout.addSpacing(8)
        header_layout.addWidget(end_button)

        header_widget.setLayout(header_layout)
        top_layout.addWidget(header_widget)

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

    # ------------------------- KIOSK ENFORCEMENT -------------------------
    def _on_app_state_changed(self, state: Qt.ApplicationState) -> None:
        """Detect when the app becomes inactive (likely app switching) and warn."""
        if state == Qt.ApplicationInactive:
            self._record_violation("Application switched or unfocused")
            # Try to bring our window back to the foreground
            QTimer.singleShot(0, self._enforce_foreground)

    def _enforce_foreground(self) -> None:
        """Re-assert full-screen and top-most, and reclaim keyboard focus."""
        try:
            self.raise_()
            self.activateWindow()
            # Re-assert full screen in case it was minimized
            self.showFullScreen()
            self.grabKeyboard()
        except Exception:
            pass

    def keyPressEvent(self, event: QKeyEvent) -> None:  # type: ignore[override]
        """Intercept special keys/combos and treat as violations, otherwise forward to focused widget."""
        if self._handle_forbidden_key(event):
            event.accept()
            return

        # When keyboard is grabbed by the window, forward non-forbidden keys to the focused widget
        fw = self.focusWidget()
        if fw is not None and fw is not self:
            try:
                clone = QKeyEvent(event.type(), event.key(), event.modifiers(), event.text(), event.isAutoRepeat(), event.count())
            except Exception:
                clone = QKeyEvent(event.type(), event.key(), event.modifiers(), event.text())
            QCoreApplication.sendEvent(fw, clone)
            event.accept()
            return

        super().keyPressEvent(event)

    def _handle_forbidden_key(self, event: QKeyEvent) -> bool:
        key = event.key()
        mods = event.modifiers()

        # Common OS/system switching or exit shortcuts
        # Alt+Tab (app switch) - often not delivered to app, but handle when it is
        if key == Qt.Key_Tab and (mods & Qt.AltModifier):
            self._record_violation("Alt+Tab detected")
            return True

        # Alt+F4 (close window)
        if key == Qt.Key_F4 and (mods & Qt.AltModifier):
            self._record_violation("Alt+F4 detected")
            return True

        # Windows/Meta key
        if key in (Qt.Key_Meta, Qt.Key_Super_L, Qt.Key_Super_R):
            self._record_violation("Windows key detected")
            return True

        # Ctrl+Esc (Start menu)
        if key == Qt.Key_Escape and (mods & Qt.ControlModifier):
            self._record_violation("Ctrl+Esc detected")
            return True

        # Ctrl+Shift+Esc (Task Manager)
        if key == Qt.Key_Escape and (mods & Qt.ControlModifier) and (mods & Qt.ShiftModifier):
            self._record_violation("Ctrl+Shift+Esc detected")
            return True

        # Alt key alone pressed (potential attempt)
        if key == Qt.Key_Alt:
            self._record_violation("Alt key detected")
            return True

        return False

    def _record_violation(self, reason: str) -> None:
        """Increment violation count (with minor throttle) and update UI; end if limit reached."""
        now = time.monotonic()
        # Throttle duplicate signals within 0.75s
        if now - self._last_violation_ts < 0.75:
            return
        self._last_violation_ts = now

        self.violation_count += 1
        remaining = max(0, self.violation_limit - self.violation_count)

        # Update warning banner
        if self.warning_label is not None:
            self.warning_label.setText(f"Warning {self.violation_count}/{self.violation_limit}: {reason}")
            self.warning_label.setVisible(True)
            # Auto-hide after a short delay if not disqualified
            if self.violation_count < self.violation_limit:
                QTimer.singleShot(3000, lambda: self.warning_label and self.warning_label.setVisible(False))

        # End test after limit reached
        if self.violation_count >= self.violation_limit:
            # Give a brief moment for UI to show, then end
            QTimer.singleShot(500, self.end_test)

    # ------------------------- TIMER LOGIC -------------------------
    def _init_countdown_timer(self) -> None:
        """Initialize and start countdown if duration > 0."""
        # Ensure initial label text and color
        self._update_timer_label()

        if self.remaining_seconds <= 0:
            return
        self._countdown_timer = QTimer(self)
        self._countdown_timer.timeout.connect(self._tick_countdown)
        self._countdown_timer.start(1000)

    def _tick_countdown(self) -> None:
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self._update_timer_label()
            if self.remaining_seconds == 0 and self._countdown_timer is not None:
                self._countdown_timer.stop()
                # Time up: end test (save and close)
                self.end_test()
                
    def end_test(self) -> None:
        """Save answers and close the application safely (idempotent)."""
        if self._ending:
            return
        self._ending = True
        try:
            # Perform a final save (blocking post)
            self.save_answer()
        finally:
            # Close the app regardless of save outcome
            QGuiApplication.quit()

    def _update_timer_label(self) -> None:
        if self.timer_label is None:
            return
        self.timer_label.setText(self._format_seconds(self.remaining_seconds))
        # Change color based on remaining time
        color = "#2e7d32"  # green
        if self.remaining_seconds <= 60:
            color = "#d32f2f"  # red
        elif self.remaining_seconds <= 5 * 60:
            color = "#f57c00"  # orange
        self.timer_label.setStyleSheet(
            f"font-size: 18px; font-weight: bold; padding: 10px; color: {color};"
        )

    @staticmethod
    def _format_seconds(total_seconds: int) -> str:
        if total_seconds < 0:
            total_seconds = 0
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

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