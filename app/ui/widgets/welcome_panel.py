"""
Painel de boas-vindas exibido na aba "Início".
Apresenta o logo/título e um botão para abrir um projeto.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class WelcomePanel(QWidget):
    """Tela inicial com botão 'Abrir Projeto'."""

    open_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(24)

        # Título
        title = QLabel("MugemUI")
        font_title = QFont()
        font_title.setPointSize(36)
        font_title.setBold(True)
        title.setFont(font_title)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Subtítulo
        subtitle = QLabel("Editor gráfico para projetos Ikemen GO / MUGEN")
        font_sub = QFont()
        font_sub.setPointSize(14)
        subtitle.setFont(font_sub)
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #888888;")
        layout.addWidget(subtitle)

        layout.addSpacing(32)

        # Botão principal
        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignCenter)

        btn_open = QPushButton("Abrir Projeto…")
        btn_open.setFixedSize(220, 48)
        font_btn = QFont()
        font_btn.setPointSize(13)
        btn_open.setFont(font_btn)
        btn_open.clicked.connect(self.open_requested)
        btn_row.addWidget(btn_open)

        layout.addLayout(btn_row)

        layout.addSpacing(24)

        # Dica
        hint = QLabel(
            "Aponte para a pasta raiz do Ikemen GO que contém <b>system.def</b>"
        )
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        layout.addWidget(hint)
