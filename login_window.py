
from PySide6.QtWidgets import QMainWindow, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap

from test_list_window import TestListWindow
from config import Endpoints
import os
from pathlib import Path

class MainWindow(QMainWindow):
    # Emits (tests: list[dict], email: str, token: str)
    login_success = Signal(list, str, str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Quantum Scholar - AI Proctored Exams (Login)")

        container = QWidget()
        self.setCentralWidget(container)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        
        # Logo
        logo_label = QLabel(self)
        # Robust asset path resolution
        asset_path = Path(__file__).resolve().parent / "assets" / "Qubitopia-logo-transparent.png"
        pixmap = QPixmap(str(asset_path))
        pixmap = pixmap.scaledToWidth(250, Qt.SmoothTransformation)
        logo_label.setPixmap(pixmap)
        logo_label.setAlignment(Qt.AlignCenter)

        # Title label with custom font
        label = QLabel("Welcome to Quantum Scholar - AI Proctored Exams!", self)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-family: 'Segoe UI'; font-size: 28px; font-weight: bold; color: #0d6efd; margin-bottom: 16px;")

        # Email label and input with custom font
        email_label = QLabel("Email:", self)
        email_label.setAlignment(Qt.AlignCenter)
        email_label.setStyleSheet("font-family: 'Segoe UI'; font-size: 16px; font-weight: 600; color: #444;")
        email_input = QLineEdit(self)
        email_input.setPlaceholderText("Enter your email")
        email_input.setAlignment(Qt.AlignCenter)
        email_input.setMinimumWidth(300)
        email_input.setStyleSheet("font-family: 'Segoe UI'; font-size: 15px; padding: 6px; border-radius: 8px; border: 1px solid #aaa;")
        self.email_input = email_input

        # Birthdate label and calendar input with custom font
        birthdate_label = QLabel("Birthdate:", self)
        birthdate_label.setAlignment(Qt.AlignCenter)
        birthdate_label.setStyleSheet("font-family: 'Segoe UI'; font-size: 16px; font-weight: 600; color: #444;")
        from PySide6.QtWidgets import QDateEdit
        birthdate_input = QDateEdit(self)
        birthdate_input.setCalendarPopup(True)
        birthdate_input.setAlignment(Qt.AlignCenter)
        birthdate_input.setDisplayFormat("dd-MM-yyyy")
        self.birthdate_input = birthdate_input
        # birthdate_input.setStyleSheet("font-family: 'Segoe UI'; font-size: 15px; padding: 6px; border-radius: 8px; border: 1px solid #aaa;")

        # Login button with custom style
        login_button = QPushButton("Login", self)
        login_button.setDefault(True)
        login_button.setStyleSheet("font-family: 'Segoe UI'; font-size: 17px; font-weight: bold; background-color: #2a2a72; color: white; border-radius: 10px; padding: 8px 24px; margin-top: 18px;")
        login_button.clicked.connect(self.login)

        # Add widgets with alignment to prevent horizontal stretching
        layout.addWidget(logo_label, alignment=Qt.AlignHCenter)
        layout.addWidget(label, alignment=Qt.AlignHCenter)
        layout.addWidget(email_label, alignment=Qt.AlignHCenter)
        layout.addWidget(email_input, alignment=Qt.AlignHCenter)
        layout.addWidget(birthdate_label, alignment=Qt.AlignHCenter)
        layout.addWidget(birthdate_input, alignment=Qt.AlignHCenter)
        layout.addWidget(login_button, alignment=Qt.AlignHCenter)

        container.setLayout(layout)

        # Open window maximized (not exclusive fullscreen)
        self.showMaximized()
        
    def login(self):
        import requests
        from PySide6.QtWidgets import QMessageBox
        email = self.email_input.text()
        birthdate = self.birthdate_input.date().toString("yyyy-MM-dd")
        url = Endpoints.LOGIN
        payload = {
            "email": email,
            "birthdate": birthdate
        }
        try:
            response = requests.post(url, json=payload)
            data = response.json()
            if response.status_code == 200:
                if "token" in data and "tests" in data:
                    # Securely store the token
                    import json as pyjson
                    token = data["token"]
                    home = os.path.expanduser("~")
                    token_path = os.path.join(home, ".quantum_scholar_token")
                    with open(token_path, "w") as f:
                        pyjson.dump({"token": token}, f)
                    # Show test list window with received tests
                    tests = data["tests"]
                    # Emit signal for controller or fallback to direct navigation
                    try:
                        self.login_success.emit(tests, email, token)
                    except Exception:
                        # Fallback: direct navigation
                        self.test_list_window = TestListWindow(tests, email, token)
                        self.test_list_window.show()
                        self.close()
                else:
                    QMessageBox.critical(self, "Login Failed", data.get("message", "Unknown error"))
            else:
                error_msg = data.get("message", response.text)
                QMessageBox.critical(self, "Login Failed", error_msg)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))