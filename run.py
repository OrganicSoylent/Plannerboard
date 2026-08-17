import sys

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from plannerboard.config import Config
from plannerboard.data.events_db import init_db
from plannerboard.ui.main_window import MainWindow
from plannerboard.ui.theme import STYLESHEET


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Plannerboard")
    app.setOrganizationName("plannerboard")
    app.setStyleSheet(STYLESHEET)

    config = Config()
    init_db()

    window = MainWindow(config)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
