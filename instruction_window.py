from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QPushButton, QMessageBox
from PySide6.QtCore import Qt
from config import Endpoints
import requests

class InstructionWindow(QMainWindow):
    def __init__(self, instructions, attempt_id, on_start_test, email, token, test_id):
        super().__init__()
        self.setWindowTitle("Quantum Scholar - AI Proctored Exams (Instructions)")
        # Set exclusive fullscreen
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.showFullScreen()

        # Store context for starting test
        self.instructions = instructions
        self.attempt_id = attempt_id
        self.on_start_test = on_start_test
        self.email = email
        self.token = token
        self.test_id = test_id

        # Main widget and layout
        central_widget = QWidget()
        layout = QVBoxLayout()

        # Scrollable instructions
        from PySide6.QtWidgets import QTextEdit, QSizePolicy
        instruction_box = QTextEdit()
        instruction_box.setReadOnly(True)
        instruction_box.setText(instructions)
        instruction_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(instruction_box)

        # Start Test button
        start_button = QPushButton("Start Test")
        start_button.setFixedHeight(50)
        start_button.setStyleSheet("font-size: 18px;")
        start_button.clicked.connect(self._start_test)
        layout.addWidget(start_button)

        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def _start_test(self):
        print(self.test_id)
        print(self.attempt_id)
        payload = {
            "email": self.email,
            "token": self.token,
            "test_id": int(self.test_id),
            "attempt_id": int(self.attempt_id),
        }
        try:
            response = requests.post(Endpoints.START_TEST, json=payload, timeout=15)
            data = response.json()
            if response.status_code == 200:
                # Expecting: {"message": "Test started successfully", "question_json": attempt.QuestionJSON}
                question_json = data.get("question_json")
                if question_json is None:
                    QMessageBox.critical(self, "Start Test Failed", "Missing question_json in response.")
                    return
                from test_window import TestWindow
                self.test_window = TestWindow(
                    email=self.email,
                    token=self.token,
                    test_id=int(self.test_id),
                    attempt_id=int(self.attempt_id),
                    question_json=question_json,
                )
                self.test_window.show()
                # Notify callback (if any)
                try:
                    if callable(self.on_start_test):
                        self.on_start_test()
                finally:
                    self.close()
            else:
                error_msg = data.get("message", response.text)
                QMessageBox.critical(self, "Start Test Failed", error_msg)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
        