"""
Editor de personagens do Ikemen GO.

Layout:
  QSplitter (Horizontal)
    Esquerda: Seletor de personagem + lista de arquivos
    Direita:
      QTabWidget (um tab por arquivo .CNS/.CMD aberto)
        QPlainTextEdit + MugenHighlighter
"""

from __future__ import annotations

import os

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.character import CharacterFiles, load_character
from app.core.project import IkemenProject
from app.ui.syntax.mugen_highlighter import MugenHighlighter


class CharacterEditor(QWidget):
    """Editor de arquivos .CNS/.CMD com syntax highlighting."""

    changed = Signal()

    def __init__(self, project: IkemenProject, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._project = project
        self._char_files: CharacterFiles | None = None
        self._open_files: dict[str, str] = {}   # path → conteúdo original
        self._modified: set[str] = set()

        self._build_ui()
        self._populate_char_list()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # --- Esquerda ---
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        # Seletor de personagem
        lbl_char = QLabel("Personagem:")
        self._combo_char = QComboBox()
        self._combo_char.currentIndexChanged.connect(self._on_char_selected)
        left_layout.addWidget(lbl_char)
        left_layout.addWidget(self._combo_char)

        # Ou abrir .def manualmente
        btn_open = QPushButton("Abrir .def manualmente…")
        btn_open.clicked.connect(self._browse_def)
        left_layout.addWidget(btn_open)

        # Lista de arquivos do personagem
        lbl_files = QLabel("Arquivos:")
        self._list_files = QListWidget()
        self._list_files.setSelectionMode(QAbstractItemView.SingleSelection)
        self._list_files.itemDoubleClicked.connect(self._on_file_double_clicked)
        left_layout.addWidget(lbl_files)
        left_layout.addWidget(self._list_files, 1)

        # Info do personagem
        self._lbl_info = QLabel("")
        self._lbl_info.setWordWrap(True)
        self._lbl_info.setStyleSheet("color: #888; font-size: 11px;")
        left_layout.addWidget(self._lbl_info)

        splitter.addWidget(left)
        left.setMaximumWidth(260)

        # --- Direita: editor ---
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self._tab_widget = QTabWidget()
        self._tab_widget.setTabsClosable(True)
        self._tab_widget.tabCloseRequested.connect(self._on_tab_close)
        right_layout.addWidget(self._tab_widget)

        splitter.addWidget(right)
        splitter.setSizes([240, 760])

    # ------------------------------------------------------------------
    # Preenchimento
    # ------------------------------------------------------------------

    def _populate_char_list(self) -> None:
        self._combo_char.blockSignals(True)
        self._combo_char.clear()
        self._combo_char.addItem("— Selecione um personagem —", "")
        for char_name in self._project.list_characters():
            def_path = os.path.join(
                self._project.chars_dir, char_name, f"{char_name}.def"
            )
            self._combo_char.addItem(char_name, def_path)
        self._combo_char.blockSignals(False)

    # ------------------------------------------------------------------
    # Seleção de personagem
    # ------------------------------------------------------------------

    @Slot(int)
    def _on_char_selected(self, index: int) -> None:
        def_path = self._combo_char.itemData(index)
        if def_path:
            self._load_character_def(def_path)

    @Slot()
    def _browse_def(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir arquivo .def de personagem",
            self._project.chars_dir or self._project.root,
            "DEF Files (*.def)",
        )
        if path:
            self._load_character_def(path)

    def _load_character_def(self, def_path: str) -> None:
        try:
            self._char_files = load_character(def_path)
        except Exception as exc:
            self._lbl_info.setText(f"Erro: {exc}")
            return

        cf = self._char_files
        self._lbl_info.setText(
            f"<b>{cf.display_name or cf.name}</b><br>"
            f"Autor: {cf.author or 'desconhecido'}"
        )
        self._populate_file_list()

    def _populate_file_list(self) -> None:
        self._list_files.clear()
        if self._char_files is None:
            return

        cf = self._char_files
        groups = [
            ("DEF", [cf.def_path]),
            ("CNS", cf.cns_paths),
            ("CMD", cf.cmd_paths),
            ("SFF", [cf.sff_path] if cf.sff_path else []),
            ("SND", [cf.snd_path] if cf.snd_path else []),
            ("AIR", [cf.air_path] if cf.air_path else []),
        ]
        for label, paths in groups:
            for path in paths:
                if path and os.path.isfile(path):
                    item = QListWidgetItem(f"[{label}] {os.path.basename(path)}")
                    item.setData(Qt.UserRole, path)
                    self._list_files.addItem(item)

    # ------------------------------------------------------------------
    # Abrir arquivos no editor
    # ------------------------------------------------------------------

    @Slot(QListWidgetItem)
    def _on_file_double_clicked(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.UserRole)
        if path:
            ext = os.path.splitext(path)[1].lower()
            if ext in (".cns", ".cmd", ".def", ".air", ".st"):
                self._open_text_file(path)

    def _open_text_file(self, path: str) -> None:
        # Verifica se já está aberto
        for i in range(self._tab_widget.count()):
            editor = self._tab_widget.widget(i)
            if getattr(editor, "_file_path", None) == path:
                self._tab_widget.setCurrentIndex(i)
                return

        from app.utils.encoding import read_text
        try:
            content, encoding = read_text(path)
        except Exception as exc:
            return

        editor = _TextEditor(path, content, encoding)
        editor.content_changed.connect(self._on_editor_changed)
        tab_name = os.path.basename(path)
        idx = self._tab_widget.addTab(editor, tab_name)
        self._tab_widget.setCurrentIndex(idx)

    @Slot(str)
    def _on_editor_changed(self, path: str) -> None:
        self._modified.add(path)
        # Atualiza título da aba com '*'
        for i in range(self._tab_widget.count()):
            ed = self._tab_widget.widget(i)
            if getattr(ed, "_file_path", None) == path:
                name = os.path.basename(path)
                self._tab_widget.setTabText(i, f"*{name}")
                break
        self.changed.emit()

    @Slot(int)
    def _on_tab_close(self, index: int) -> None:
        self._tab_widget.removeTab(index)


class _TextEditor(QWidget):
    """Widget de edição de texto com syntax highlighting."""

    content_changed = Signal(str)   # emite o path do arquivo

    def __init__(self, path: str, content: str, encoding: str) -> None:
        super().__init__()
        self._file_path = path
        self._encoding = encoding

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._edit = QPlainTextEdit()
        font = QFont("Consolas", 10)
        font.setFixedPitch(True)
        self._edit.setFont(font)
        self._edit.setLineWrapMode(QPlainTextEdit.NoWrap)
        self._edit.setPlainText(content)

        ext = os.path.splitext(path)[1].lower()
        if ext in (".cns", ".cmd", ".def", ".st", ".air"):
            self._highlighter = MugenHighlighter(self._edit.document())

        self._edit.textChanged.connect(
            lambda: self.content_changed.emit(self._file_path)
        )
        layout.addWidget(self._edit)

        # Barra de status interna
        self._lbl_status = QLabel(f"  {os.path.basename(path)}  [{encoding}]")
        self._lbl_status.setStyleSheet("background: #2d2d2d; color: #ccc; font-size: 10px;")
        self._lbl_status.setFixedHeight(18)
        layout.addWidget(self._lbl_status)

    def save(self) -> None:
        from app.utils.encoding import write_text
        write_text(self._file_path, self._edit.toPlainText(), self._encoding)

    def content(self) -> str:
        return self._edit.toPlainText()
