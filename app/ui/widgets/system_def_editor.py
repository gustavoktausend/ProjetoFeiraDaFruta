"""
Editor visual para o arquivo system.def do Ikemen GO.

Layout:
  QScrollArea
    QWidget (content)
      QVBoxLayout
        per seção: QGroupBox > QFormLayout
          por parâmetro: label + widget específico
"""

from __future__ import annotations

import os

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.core import ini_parser
from app.core.project import IkemenProject
from app.core.system_def import KNOWN_SECTIONS, KNOWN_SECTIONS_MAP, ParamDef, ParamType, SectionDef


class SystemDefEditor(QScrollArea):
    """Formulário visual do system.def organizado por seções."""

    changed = Signal()

    def __init__(self, project: IkemenProject, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._project = project
        self._doc: ini_parser.MugenIniDocument | None = None
        self._widgets: dict[tuple[str, str], QWidget] = {}  # (secname, key) -> widget
        self._loading = False

        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._content = QWidget()
        self._layout = QVBoxLayout(self._content)
        self._layout.setAlignment(Qt.AlignTop)
        self._layout.setSpacing(12)
        self.setWidget(self._content)

        self._load_file()

    # ------------------------------------------------------------------
    # Carregamento
    # ------------------------------------------------------------------

    def _load_file(self) -> None:
        path = self._project.system_def
        if not path or not os.path.isfile(path):
            self._show_error(f"system.def não encontrado: {path}")
            return

        try:
            self._doc = ini_parser.load(path)
        except Exception as exc:
            self._show_error(f"Erro ao carregar system.def:\n{exc}")
            return

        self._build_ui()

    def _show_error(self, msg: str) -> None:
        lbl = QLabel(msg)
        lbl.setStyleSheet("color: red;")
        lbl.setWordWrap(True)
        self._layout.addWidget(lbl)

    # ------------------------------------------------------------------
    # Construção dos formulários
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        if self._doc is None:
            return

        self._loading = True

        # Seções conhecidas primeiro (na ordem definida)
        rendered_sections: set[str] = set()

        for sec_def in KNOWN_SECTIONS:
            doc_section = self._doc.section(sec_def.name)
            group = self._build_section_group(sec_def, doc_section)
            self._layout.addWidget(group)
            rendered_sections.add(sec_def.name.lower())

        # Seções desconhecidas (não mapeadas)
        for doc_sec in self._doc.sections:
            if doc_sec.name.lower() in rendered_sections:
                continue
            # Cria SectionDef genérica com os parâmetros presentes
            generic_def = SectionDef(
                name=doc_sec.name,
                label=f"[{doc_sec.name}]",
                description="Seção não mapeada — edição em texto livre",
            )
            params = []
            for entry in doc_sec.entries:
                if entry.key:
                    params.append(ParamDef(entry.key, entry.key, ParamType.STRING))
            generic_def.params = params
            group = self._build_section_group(generic_def, doc_sec)
            self._layout.addWidget(group)
            rendered_sections.add(doc_sec.name.lower())

        self._layout.addStretch()
        self._loading = False

    def _build_section_group(
        self,
        sec_def: SectionDef,
        doc_section: ini_parser.IniSection | None,
    ) -> QGroupBox:
        group = QGroupBox(sec_def.label)
        font = QFont()
        font.setBold(True)
        group.setFont(font)

        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.setSpacing(8)
        form.setContentsMargins(12, 16, 12, 12)

        if sec_def.description:
            desc_lbl = QLabel(sec_def.description)
            desc_lbl.setStyleSheet("color: #888888; font-weight: normal;")
            desc_lbl.setWordWrap(True)
            f = QFont()
            f.setBold(False)
            desc_lbl.setFont(f)
            form.addRow(desc_lbl)

        for param in sec_def.params:
            current_value = ""
            if doc_section:
                current_value = doc_section.get(param.key)
            if not current_value:
                current_value = str(param.default)

            widget = self._create_param_widget(param, current_value, sec_def.name)
            label = QLabel(param.label + ":")
            label_font = QFont()
            label_font.setBold(False)
            label.setFont(label_font)
            if param.description:
                label.setToolTip(param.description)
                widget.setToolTip(param.description)
            form.addRow(label, widget)

        return group

    def _create_param_widget(
        self, param: ParamDef, value: str, section_name: str
    ) -> QWidget:
        """Cria o widget adequado para o tipo do parâmetro."""
        key_tuple = (section_name.lower(), param.key.lower())

        if param.ptype == ParamType.BOOL:
            cb = QCheckBox()
            cb.setChecked(value.strip() not in ("0", "", "false", "no"))
            cb.stateChanged.connect(
                lambda state, k=key_tuple: self._on_bool_changed(k, state)
            )
            self._widgets[key_tuple] = cb
            return cb

        if param.ptype == ParamType.INT:
            sb = QSpinBox()
            sb.setRange(-9999999, 9999999)
            sb.setValue(_to_int(value))
            sb.valueChanged.connect(
                lambda v, k=key_tuple: self._on_int_changed(k, v)
            )
            self._widgets[key_tuple] = sb
            return sb

        if param.ptype == ParamType.FILE:
            return self._create_file_widget(param, value, key_tuple, section_name)

        if param.ptype == ParamType.COLOR:
            le = QLineEdit(value)
            le.setPlaceholderText("R, G, B")
            le.setMaximumWidth(120)
            le.textChanged.connect(
                lambda t, k=key_tuple: self._on_text_changed(k, t)
            )
            self._widgets[key_tuple] = le
            return le

        # Default: STRING / ENUM / FLOAT
        le = QLineEdit(value)
        le.textChanged.connect(
            lambda t, k=key_tuple: self._on_text_changed(k, t)
        )
        self._widgets[key_tuple] = le
        return le

    def _create_file_widget(
        self,
        param: ParamDef,
        value: str,
        key_tuple: tuple[str, str],
        section_name: str,
    ) -> QWidget:
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)

        le = QLineEdit(value)
        le.textChanged.connect(
            lambda t, k=key_tuple: self._on_text_changed(k, t)
        )
        self._widgets[key_tuple] = le
        row.addWidget(le)

        btn = QPushButton("…")
        btn.setFixedWidth(28)
        btn.clicked.connect(
            lambda checked, field=le: self._browse_file(field)
        )
        row.addWidget(btn)
        return container

    # ------------------------------------------------------------------
    # Slots de alteração
    # ------------------------------------------------------------------

    def _on_text_changed(self, key: tuple[str, str], text: str) -> None:
        if not self._loading:
            self._apply_change(key, text)

    def _on_bool_changed(self, key: tuple[str, str], state: int) -> None:
        if not self._loading:
            self._apply_change(key, "1" if state else "0")

    def _on_int_changed(self, key: tuple[str, str], value: int) -> None:
        if not self._loading:
            self._apply_change(key, str(value))

    def _apply_change(self, key: tuple[str, str], value: str) -> None:
        if self._doc is None:
            return
        section_name, param_key = key
        # Procura a seção pelo nome
        for sec in self._doc.sections:
            if sec.name.lower() == section_name:
                sec.set(param_key, value)
                break
        self.changed.emit()

    @Slot()
    def _browse_file(self, field: QLineEdit) -> None:
        project_root = self._project.root
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar Arquivo",
            project_root,
        )
        if path:
            try:
                import os
                rel = os.path.relpath(path, project_root).replace("\\", "/")
                field.setText(rel)
            except ValueError:
                field.setText(path)

    # ------------------------------------------------------------------
    # Salvar
    # ------------------------------------------------------------------

    def save(self) -> None:
        if self._doc is None:
            return
        self._doc.save(self._project.system_def)


def _to_int(value: str) -> int:
    try:
        return int(value.strip().split(",")[0].strip())
    except (ValueError, IndexError):
        return 0
