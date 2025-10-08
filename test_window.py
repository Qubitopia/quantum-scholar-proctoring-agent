from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QPushButton, QMessageBox
from PySide6.QtCore import Qt

class TestWindow(QMainWindow):
    def __init__(self, email, token, test_id, attempt_id, question_json):
        super().__init__()
        self.setWindowTitle("Quantum Scholar - AI Proctored Exams (Test)")
        # Set exclusive fullscreen
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.showFullScreen()

        # Store context
        self.email = email
        self.token = token
        self.test_id = test_id
        self.attempt_id = attempt_id
        self.question_json = question_json

        # Minimal placeholder UI to confirm navigation worked
        central_widget = QWidget()
        layout = QVBoxLayout()
        from PySide6.QtWidgets import QLabel
        info = QLabel(f"Test ID: {self.test_id} | Attempt ID: {self.attempt_id}")
        info.setStyleSheet("font-size: 18px; padding: 12px;")
        layout.addWidget(info)

        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)