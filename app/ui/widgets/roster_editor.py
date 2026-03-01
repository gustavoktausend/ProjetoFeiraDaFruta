"""
Editor visual do select.def (roster de personagens).

Layout:
  QSplitter (Horizontal)
    Esquerda: QListView + toolbar (Adicionar/Remover/Subir/Descer)
    Direita:  Painel de detalhes da entrada selecionada
"""

from __future__ import annotations

import os

from PySide6.QtCore import QModelIndex, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.core import select_def as sd
from app.core.project import IkemenProject
from app.ui.models.roster_model import RosterModel


class RosterEditor(QWidget):
    """Editor de drag-and-drop para o select.def."""

    changed = Signal()

    def __init__(self, project: IkemenProject, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._project = project
        self._doc: sd.SelectDefDocument | None = None
        self._model: RosterModel | None = None
        self._loading = False

        self._build_ui()
        self._load_file()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # --- Lado esquerdo: lista ---
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        self._list_view = QListView()
        self._list_view.setDragDropMode(QAbstractItemView.InternalMove)
        self._list_view.setDefaultDropAction(Qt.MoveAction)
        self._list_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self._list_view.setAlternatingRowColors(True)
        self._list_view.selectionModel
        left_layout.addWidget(self._list_view)

        # Botões
        btn_row = QHBoxLayout()
        self._btn_add = QPushButton("Adicionar")
        self._btn_remove = QPushButton("Remover")
        self._btn_up = QPushButton("▲")
        self._btn_down = QPushButton("▼")

        for btn in (self._btn_add, self._btn_remove, self._btn_up, self._btn_down):
            btn.setFixedHeight(28)
        self._btn_up.setFixedWidth(36)
        self._btn_down.setFixedWidth(36)

        btn_row.addWidget(self._btn_add)
        btn_row.addWidget(self._btn_remove)
        btn_row.addStretch()
        btn_row.addWidget(self._btn_up)
        btn_row.addWidget(self._btn_down)
        left_layout.addLayout(btn_row)

        splitter.addWidget(left)

        # --- Lado direito: detalhes ---
        self._detail_panel = DetailPanel(self._project)
        self._detail_panel.changed.connect(self._on_detail_changed)
        scroll = QScrollArea()
        scroll.setWidget(self._detail_panel)
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(320)
        splitter.addWidget(scroll)

        splitter.setSizes([400, 320])

        # Conexões
        self._btn_add.clicked.connect(self._on_add)
        self._btn_remove.clicked.connect(self._on_remove)
        self._btn_up.clicked.connect(self._on_move_up)
        self._btn_down.clicked.connect(self._on_move_down)

    # ------------------------------------------------------------------
    # Carregamento
    # ------------------------------------------------------------------

    def _load_file(self) -> None:
        path = self._project.select_def
        if not path or not os.path.isfile(path):
            return
        try:
            self._doc = sd.load(path)
        except Exception as exc:
            return

        self._model = RosterModel(self._doc)
        self._list_view.setModel(self._model)
        self._list_view.selectionModel().currentChanged.connect(self._on_selection)
        self._model.dataChanged.connect(lambda *_: self.changed.emit())
        self._model.rowsMoved.connect(lambda *_: self.changed.emit())
        self._model.rowsInserted.connect(lambda *_: self.changed.emit())
        self._model.rowsRemoved.connect(lambda *_: self.changed.emit())

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    @Slot()
    def _on_add(self) -> None:
        if self._model is None or self._doc is None:
            return
        # Abre diálogo para escolher nome do personagem
        chars = self._project.list_characters()
        dlg = AddCharacterDialog(chars, self._project, self)
        if dlg.exec():
            entry = dlg.get_entry()
            if entry:
                self._model.add_character(entry)

    @Slot()
    def _on_remove(self) -> None:
        if self._model is None:
            return
        idx = self._list_view.currentIndex()
        if idx.isValid():
            self._model.remove_character(idx.row())

    @Slot()
    def _on_move_up(self) -> None:
        self._move_selected(-1)

    @Slot()
    def _on_move_down(self) -> None:
        self._move_selected(1)

    def _move_selected(self, delta: int) -> None:
        if self._model is None or self._doc is None:
            return
        idx = self._list_view.currentIndex()
        if not idx.isValid():
            return
        row = idx.row()
        new_row = row + delta
        if 0 <= new_row < self._model.rowCount():
            self._doc.move_character(row, new_row)
            self._model.refresh()
            new_idx = self._model.index(new_row)
            self._list_view.setCurrentIndex(new_idx)
            self.changed.emit()

    @Slot(QModelIndex, QModelIndex)
    def _on_selection(self, current: QModelIndex, previous: QModelIndex) -> None:
        if self._model is None:
            return
        entry = self._model.entry_at(current.row())
        self._detail_panel.set_entry(entry, current.row())

    @Slot()
    def _on_detail_changed(self) -> None:
        if self._model:
            self._model.refresh()
        self.changed.emit()

    # ------------------------------------------------------------------
    # Salvar
    # ------------------------------------------------------------------

    def save(self) -> None:
        if self._doc:
            self._doc.save(self._project.select_def)


class DetailPanel(QWidget):
    """Painel de detalhes de uma entrada do roster."""

    changed = Signal()

    def __init__(self, project: IkemenProject, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._project = project
        self._entry: sd.CharEntry | None = None
        self._index: int = -1
        self._loading = False
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)

        grp = QGroupBox("Detalhes da Entrada")
        form = QFormLayout(grp)
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(8)
        layout.addWidget(grp)

        self._le_name = QLineEdit()
        self._le_name.setPlaceholderText("Nome ou caminho do personagem")
        form.addRow("Personagem:", self._le_name)

        stage_row = QWidget()
        stage_layout = QHBoxLayout(stage_row)
        stage_layout.setContentsMargins(0, 0, 0, 0)
        self._le_stage = QLineEdit()
        self._le_stage.setPlaceholderText("stages/stage.def (opcional)")
        self._btn_stage = QPushButton("…")
        self._btn_stage.setFixedWidth(28)
        stage_layout.addWidget(self._le_stage)
        stage_layout.addWidget(self._btn_stage)
        form.addRow("Stage:", stage_row)

        self._le_music = QLineEdit()
        self._le_music.setPlaceholderText("musica.mp3 (opcional)")
        form.addRow("Música:", self._le_music)

        self._le_opts = QLineEdit()
        self._le_opts.setPlaceholderText("includestage=1, outro=val")
        form.addRow("Opções extras:", self._le_opts)

        self._lbl_raw = QLabel()
        self._lbl_raw.setWordWrap(True)
        self._lbl_raw.setStyleSheet("color: #777; font-size: 11px;")
        layout.addWidget(self._lbl_raw)

        layout.addStretch()

        # Conexões
        self._le_name.textChanged.connect(self._on_changed)
        self._le_stage.textChanged.connect(self._on_changed)
        self._le_music.textChanged.connect(self._on_changed)
        self._le_opts.textChanged.connect(self._on_changed)
        self._btn_stage.clicked.connect(self._browse_stage)

        self.setEnabled(False)

    def set_entry(self, entry: sd.CharEntry | None, index: int) -> None:
        self._entry = entry
        self._index = index
        self._loading = True
        if entry is None:
            self.setEnabled(False)
            self._le_name.setText("")
            self._le_stage.setText("")
            self._le_music.setText("")
            self._le_opts.setText("")
        else:
            self.setEnabled(True)
            self._le_name.setText(entry.name)
            self._le_stage.setText(entry.stage)
            self._le_music.setText(entry.options.get("music", ""))
            # Demais opções (exceto music)
            extras = {k: v for k, v in entry.options.items() if k != "music"}
            self._le_opts.setText(
                ", ".join(f"{k}={v}" for k, v in extras.items())
            )
            self._lbl_raw.setText(f"Linha: {entry.to_line()}")
        self._loading = False

    @Slot()
    def _on_changed(self) -> None:
        if self._loading or self._entry is None:
            return
        self._entry.name = self._le_name.text().strip()
        self._entry.stage = self._le_stage.text().strip()

        opts: dict[str, str] = {}
        music = self._le_music.text().strip()
        if music:
            opts["music"] = music
        for item in self._le_opts.text().split(","):
            item = item.strip()
            if "=" in item:
                k, _, v = item.partition("=")
                opts[k.strip()] = v.strip()
        self._entry.options = opts
        self._lbl_raw.setText(f"Linha: {self._entry.to_line()}")
        self.changed.emit()

    @Slot()
    def _browse_stage(self) -> None:
        root = self._project.root
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar Stage", root, "Stage DEF (*.def)"
        )
        if path:
            try:
                rel = os.path.relpath(path, root).replace("\\", "/")
                self._le_stage.setText(rel)
            except ValueError:
                self._le_stage.setText(path)


class AddCharacterDialog(QWidget):
    """Diálogo simples para adicionar um personagem ao roster."""

    def __init__(
        self,
        available_chars: list[str],
        project: IkemenProject,
        parent: QWidget | None = None,
    ) -> None:
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QComboBox
        self._dialog = QDialog(parent)
        self._dialog.setWindowTitle("Adicionar Personagem")
        self._dialog.resize(400, 160)

        layout = QVBoxLayout(self._dialog)
        form = QFormLayout()

        self._combo = QComboBox()
        self._combo.setEditable(True)
        self._combo.addItems(available_chars)
        form.addRow("Personagem:", self._combo)

        self._le_stage = QLineEdit()
        self._le_stage.setPlaceholderText("stages/stage.def (opcional)")
        form.addRow("Stage:", self._le_stage)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._dialog.accept)
        buttons.rejected.connect(self._dialog.reject)
        layout.addWidget(buttons)

        self._result: sd.CharEntry | None = None

    def exec(self) -> bool:
        from PySide6.QtWidgets import QDialog
        result = self._dialog.exec()
        if result == QDialog.Accepted:
            name = self._combo.currentText().strip()
            if name:
                self._result = sd.CharEntry(
                    name=name,
                    stage=self._le_stage.text().strip(),
                )
                return True
        return False

    def get_entry(self) -> sd.CharEntry | None:
        return self._result
