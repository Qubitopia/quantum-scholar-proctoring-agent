
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject
from PySide6 import QtGui
from login_window import MainWindow
from test_list_window import TestListWindow
from pathlib import Path


def resource_path(*parts: str) -> Path:
	"""Resolve resource paths for dev and frozen (PyInstaller) modes.

	When frozen, files are next to the executable in dist; _MEIPASS points to
	the temp unpack dir for onefile, but in onedir we can still rely on cwd/MEIPASS.
	"""
	base = getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)
	return Path(base, *parts)

class AppController(QObject):
	def __init__(self):
		super().__init__()
		self.app = QApplication(sys.argv)
		icon_path = resource_path('assets', 'Qubitopia-logo-transparent.png')
		self.app.setWindowIcon(QtGui.QIcon(str(icon_path)))
		self.login_window = MainWindow()
		self.login_window.login_success.connect(self.show_test_list_window)
		self.test_list_window = None

	def show_login_window(self):
		self.login_window.show()

	def show_test_list_window(self, tests, email, token):
		self.test_list_window = TestListWindow(tests, email, token)
		self.test_list_window.show()
		self.login_window.close()

	def run(self):
		self.show_login_window()
		self.app.exec()

if __name__ == "__main__":
	controller = AppController()
	controller.run()
        