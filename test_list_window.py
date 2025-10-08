from PySide6.QtWidgets import QMainWindow, QListWidget, QVBoxLayout, QWidget, QPushButton, QMessageBox
from PySide6.QtCore import Qt
from config import Endpoints
import requests

class TestListWindow(QMainWindow):
    def __init__(self, tests, email, token):
        super().__init__()
        self.setWindowTitle("Quantum Scholar - AI Proctored Exams (Tests Available)")

        # Central widget and layout
        central_widget = QWidget()
        outer_layout = QVBoxLayout()
        outer_layout.addStretch(1)

        center_widget = QWidget()
        center_layout = QVBoxLayout()

        # List widget for received tests
        self.test_list = QListWidget()
        self.test_list.setSelectionMode(QListWidget.SingleSelection)
        self.test_list.setMinimumWidth(600)
        self.test_list.setStyleSheet("font-size: 16px; padding: 8px; border-radius: 8px;")
        for test in tests:
            test_id = test.get("test_id", "N/A")
            test_name = test.get("test_name", "Unknown Test")
            start = test.get("test_start_time", "")
            end = test.get("test_end_time", "")
            display_text = f"{test_id} | {test_name} | Start: {start} | End: {end}"
            self.test_list.addItem(display_text)
        center_layout.addWidget(self.test_list, alignment=Qt.AlignHCenter)

        # Take Exam button
        self.take_exam_btn = QPushButton("Take Exam")
        self.take_exam_btn.setStyleSheet("font-size: 18px; padding: 10px 24px; background: #4f8cff; color: white; border-radius: 8px;")
        self.take_exam_btn.clicked.connect(lambda: self.take_exam(email, token))
        center_layout.addWidget(self.take_exam_btn, alignment=Qt.AlignHCenter)

        center_widget.setLayout(center_layout)
        outer_layout.addWidget(center_widget, alignment=Qt.AlignVCenter)
        outer_layout.addStretch(1)
        central_widget.setLayout(outer_layout)
        self.setCentralWidget(central_widget)

        # Open window maximized (not exclusive fullscreen)
        self.showMaximized()

    def take_exam(self, email, token):
        selected_items = self.test_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Test Selected", "Please select a test to take.")
            return
        selected_test = selected_items[0].text()
        # Extract test_id from display_text
        test_id = selected_test.split('|')[0].strip() 
        url = Endpoints.INIT_TEST
        payload = {
            "email": email,
            "token": token,
            "test_id": int(test_id)
        }
        try:
            response = requests.post(url, json=payload, timeout=10)
            data = response.json()
            if response.status_code == 200:
                # If message key exists and indicates success, proceed
                msg = data.get("message", "")
                instructions = data.get("instructions", msg)
                attempt_id = data.get("attempt_id")
                from instruction_window import InstructionWindow
                def on_start_test_success():
                    # Placeholder, actual navigation handled within InstructionWindow upon successful start
                    pass
                self.instruction_window = InstructionWindow(
                    instructions=instructions,
                    attempt_id=attempt_id,
                    on_start_test=on_start_test_success,
                    email=email,
                    token=token,
                    test_id=int(test_id)
                )
                self.instruction_window.show()
                self.close()
            else:
                error_msg = data.get("message", response.text)
                QMessageBox.critical(self, "Exam Start Failed", error_msg)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))