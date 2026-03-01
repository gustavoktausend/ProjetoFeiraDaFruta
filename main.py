"""
MugemUI — Editor gráfico para projetos Ikemen GO / MUGEN
Ponto de entrada principal.
"""

import sys
import os

# Garante que o diretório do projeto está no path
sys.path.insert(0, os.path.dirname(__file__))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from app.ui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("MugemUI")
    app.setApplicationDisplayName("MugemUI — Ikemen GO Editor")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("MugemUI")

    # Estilo base
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
