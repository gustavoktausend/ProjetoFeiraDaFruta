"""
Editor visual do arquivo .def de personagem do Ikemen GO / MUGEN.

Layout:
  QVBoxLayout:
    QLabel título ("Editando: [displayname] por [author]")
    QSplitter(Horizontal):
      Esquerda (QScrollArea): formulários por seção
      Direita: _PortraitPanel (portrait 9000,0 + status de arquivos)
"""

from __future__ import annotations

import os

from PySide6.QtCore import (
    QObject,
    QRunnable,
    QThreadPool,
    Qt,
    Signal,
    Slot,
)
from PySide6.QtGui import QColor, QFont, QImage, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)


# ------------------------------------------------------------------
# Widgets auxiliares
# ------------------------------------------------------------------

class _FileRow(QWidget):
    """Campo de arquivo com indicador de existência e botão browse."""

    changed = Signal(str)

    def __init__(self, value: str, base_dir: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._base_dir = base_dir

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._edit = QLineEdit(value)
        layout.addWidget(self._edit)

        btn = QPushButton("…")
        btn.setFixedWidth(28)
        btn.clicked.connect(self._browse)
        layout.addWidget(btn)

        self._indicator = QLabel()
        self._indicator.setFixedWidth(16)
        layout.addWidget(self._indicator)

        self._edit.textChanged.connect(self._on_text_changed)
        self._update_indicator(value)

    def _on_text_changed(self, text: str) -> None:
        self._update_indicator(text)
        self.changed.emit(text)

    def _update_indicator(self, text: str) -> None:
        if not text.strip():
            self._indicator.setText("")
            return
        full = os.path.join(self._base_dir, text) if not os.path.isabs(text) else text
        if os.path.isfile(full):
            self._indicator.setText("✓")
            self._indicator.setStyleSheet("color: #4caf50; font-weight: bold;")
        else:
            self._indicator.setText("✗")
            self._indicator.setStyleSheet("color: #f44336; font-weight: bold;")

    def text(self) -> str:
        return self._edit.text()

    def set_text(self, text: str) -> None:
        self._edit.setText(text)

    @Slot()
    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar Arquivo", self._base_dir
        )
        if path:
            try:
                rel = os.path.relpath(path, self._base_dir).replace("\\", "/")
                self._edit.setText(rel)
            except ValueError:
                self._edit.setText(path)


class _DateWidget(QWidget):
    """Widget para o campo versiondate (MM,DD,YYYY)."""

    changed = Signal(str)

    def __init__(self, value: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._month = QSpinBox()
        self._month.setRange(1, 12)
        self._month.setPrefix("M:")
        self._month.setFixedWidth(64)

        self._day = QSpinBox()
        self._day.setRange(1, 31)
        self._day.setPrefix("D:")
        self._day.setFixedWidth(64)

        self._year = QSpinBox()
        self._year.setRange(1900, 2099)
        self._year.setFixedWidth(74)

        layout.addWidget(self._month)
        layout.addWidget(QLabel("/"))
        layout.addWidget(self._day)
        layout.addWidget(QLabel("/"))
        layout.addWidget(self._year)
        layout.addStretch()

        self.set_value(value)

        self._month.valueChanged.connect(self._emit_changed)
        self._day.valueChanged.connect(self._emit_changed)
        self._year.valueChanged.connect(self._emit_changed)

    def set_value(self, text: str) -> None:
        parts = [p.strip() for p in text.split(",")]
        try:
            m = int(parts[0]) if len(parts) > 0 and parts[0] else 1
            d = int(parts[1]) if len(parts) > 1 and parts[1] else 1
            y = int(parts[2]) if len(parts) > 2 and parts[2] else 2024
        except (ValueError, IndexError):
            m, d, y = 1, 1, 2024

        self._month.blockSignals(True)
        self._day.blockSignals(True)
        self._year.blockSignals(True)
        self._month.setValue(max(1, min(12, m)))
        self._day.setValue(max(1, min(31, d)))
        self._year.setValue(max(1900, min(2099, y)))
        self._month.blockSignals(False)
        self._day.blockSignals(False)
        self._year.blockSignals(False)

    def value(self) -> str:
        return f"{self._month.value():02d},{self._day.value():02d},{self._year.value()}"

    def _emit_changed(self) -> None:
        self.changed.emit(self.value())


class _CoordWidget(QWidget):
    """Widget para o campo localcoord com dica contextual."""

    changed = Signal(str)

    def __init__(self, value: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._edit = QLineEdit(value)
        self._hint = QLabel("")
        self._hint.setStyleSheet("color: #888; font-size: 10px;")

        layout.addWidget(self._edit)
        layout.addWidget(self._hint)

        self._edit.textChanged.connect(self._on_text_changed)
        self._update_hint(value)

    def _on_text_changed(self, text: str) -> None:
        self._update_hint(text)
        self.changed.emit(text)

    def _update_hint(self, text: str) -> None:
        stripped = text.strip().replace(" ", "")
        if stripped == "320,240":
            self._hint.setText("SD (320×240)")
        elif stripped == "1280,720":
            self._hint.setText("HD (1280×720 — Ikemen GO)")
        else:
            self._hint.setText("")

    def text(self) -> str:
        return self._edit.text()


# ------------------------------------------------------------------
# Carregamento do SFF em background
# ------------------------------------------------------------------

class _PortraitSignals(QObject):
    finished = Signal(object)   # SpriteSheet
    error = Signal(str)


class _PortraitLoader(QRunnable):
    """Carrega SFF em thread secundária para extrair o portrait."""

    def __init__(self, path: str) -> None:
        super().__init__()
        self._path = path
        self.signals = _PortraitSignals()

    def run(self) -> None:
        try:
            from app.core.sff.sff_reader import load
            sheet = load(self._path)
            self.signals.finished.emit(sheet)
        except Exception as exc:
            self.signals.error.emit(str(exc))


# ------------------------------------------------------------------
# Painel de portrait (direita)
# ------------------------------------------------------------------

class _PortraitPanel(QGroupBox):
    """Painel direito com portrait, info do SFF e status de arquivos."""

    reload_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Portrait", parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Portrait grande (9000,0) — 160×160
        self._lbl_portrait = QLabel()
        self._lbl_portrait.setFixedSize(160, 160)
        self._lbl_portrait.setAlignment(Qt.AlignCenter)
        self._lbl_portrait.setStyleSheet(
            "background: #1a1a1a; border: 1px solid #444; color: #555;"
        )
        self._lbl_portrait.setText("Portrait\n(9000,0)")
        layout.addWidget(self._lbl_portrait, alignment=Qt.AlignCenter)

        lbl_p_hint = QLabel("Portrait (9000,0)")
        lbl_p_hint.setStyleSheet("color: #666; font-size: 10px;")
        lbl_p_hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_p_hint, alignment=Qt.AlignCenter)

        # Small portrait (9000,1) — 32×32
        self._lbl_small = QLabel()
        self._lbl_small.setFixedSize(32, 32)
        self._lbl_small.setAlignment(Qt.AlignCenter)
        self._lbl_small.setStyleSheet(
            "background: #1a1a1a; border: 1px solid #444; color: #555;"
        )
        self._lbl_small.setText("S")
        layout.addWidget(self._lbl_small, alignment=Qt.AlignCenter)

        lbl_s_hint = QLabel("Small (9000,1)")
        lbl_s_hint.setStyleSheet("color: #666; font-size: 10px;")
        lbl_s_hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_s_hint, alignment=Qt.AlignCenter)

        # Info do SFF
        self._lbl_info = QLabel("")
        self._lbl_info.setStyleSheet("color: #888; font-size: 10px;")
        self._lbl_info.setWordWrap(True)
        layout.addWidget(self._lbl_info)

        # Contagem de arquivos
        self._lbl_files = QLabel("")
        self._lbl_files.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(self._lbl_files)

        # Lista de status de arquivos
        self._file_list = QListWidget()
        self._file_list.setStyleSheet("font-size: 10px;")
        layout.addWidget(self._file_list, 1)

        # Botão recarregar
        btn_reload = QPushButton("Recarregar Portrait")
        btn_reload.clicked.connect(self.reload_requested.emit)
        layout.addWidget(btn_reload)

    def show_placeholder(self, msg: str) -> None:
        self._lbl_portrait.setPixmap(QPixmap())
        self._lbl_portrait.setText(msg)

    def show_portrait(self, px_large: QPixmap, px_small: QPixmap | None = None) -> None:
        scaled = px_large.scaled(160, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._lbl_portrait.setPixmap(scaled)
        self._lbl_portrait.setText("")
        if px_small is not None:
            scaled_small = px_small.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self._lbl_small.setPixmap(scaled_small)
            self._lbl_small.setText("")

    def set_sff_info(self, info: str) -> None:
        self._lbl_info.setText(info)

    def set_file_status(self, files: list[tuple[str, bool]]) -> None:
        found = sum(1 for _, exists in files if exists)
        self._lbl_files.setText(f"Arquivos: {found}/{len(files)} encontrados")
        self._file_list.clear()
        for name, exists in files:
            item = QListWidgetItem(("✓ " if exists else "✗ ") + name)
            item.setForeground(QColor("#4caf50") if exists else QColor("#f44336"))
            self._file_list.addItem(item)


# ------------------------------------------------------------------
# Editor principal
# ------------------------------------------------------------------

class DefEditor(QWidget):
    """Editor visual do arquivo .def de personagem com preview de portrait."""

    changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._doc = None
        self._def_path = ""
        self._char_dir = ""
        self._widgets: dict[tuple[str, str], QWidget] = {}
        self._loading = False
        self._pending_sff_path = ""
        self._sff_key_in_doc = "sprite"   # "sprite" ou "sff" (o que existe no doc)

        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        self._lbl_title = QLabel("Nenhum personagem carregado")
        self._lbl_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #ccc;")
        main_layout.addWidget(self._lbl_title)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter, 1)

        # Esquerda: ScrollArea com formulários
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._form_content = QWidget()
        self._form_layout = QVBoxLayout(self._form_content)
        self._form_layout.setAlignment(Qt.AlignTop)
        self._form_layout.setSpacing(12)
        self._scroll.setWidget(self._form_content)
        splitter.addWidget(self._scroll)

        # Direita: painel de portrait
        self._portrait_panel = _PortraitPanel()
        self._portrait_panel.setMinimumWidth(220)
        self._portrait_panel.reload_requested.connect(self._try_load_portrait)
        splitter.addWidget(self._portrait_panel)

        splitter.setSizes([700, 240])

    # ------------------------------------------------------------------
    # Carregamento público
    # ------------------------------------------------------------------

    def load(self, def_path: str) -> None:
        """Carrega e exibe o .def do personagem."""
        from app.core import ini_parser

        self._def_path = def_path
        self._char_dir = os.path.dirname(def_path)

        try:
            self._doc = ini_parser.load(def_path)
        except Exception as exc:
            self._lbl_title.setText(f"Erro ao carregar: {exc}")
            return

        self._clear_and_rebuild_forms()
        self._update_file_status_panel()
        self._try_load_portrait()

    # ------------------------------------------------------------------
    # Construção do formulário
    # ------------------------------------------------------------------

    def _clear_and_rebuild_forms(self) -> None:
        # Remove todos os widgets anteriores
        while self._form_layout.count():
            item = self._form_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._widgets.clear()

        self._loading = True

        if self._doc is None:
            self._loading = False
            return

        from app.core.char_def import KNOWN_SECTIONS

        # Atualiza o título com nome/autor do personagem
        info_sec = self._doc.section("Info")
        if info_sec:
            display = info_sec.get("displayname") or info_sec.get("name") or ""
            author = info_sec.get("author") or ""
            self._lbl_title.setText(
                f"Editando: {display or '(sem nome)'} por {author or 'desconhecido'}"
            )

        rendered: set[str] = set()
        for sec_def in KNOWN_SECTIONS:
            doc_section = self._doc.section(sec_def.name)
            group = self._build_section_group(sec_def, doc_section)
            self._form_layout.addWidget(group)
            rendered.add(sec_def.name.lower())

        self._form_layout.addStretch()
        self._loading = False

    def _build_section_group(self, sec_def, doc_section) -> QGroupBox:
        group = QGroupBox(sec_def.label)
        bold_font = QFont()
        bold_font.setBold(True)
        group.setFont(bold_font)

        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.setSpacing(8)
        form.setContentsMargins(12, 16, 12, 12)

        if sec_def.description:
            desc_lbl = QLabel(sec_def.description)
            desc_lbl.setStyleSheet("color: #888888; font-weight: normal;")
            desc_lbl.setWordWrap(True)
            normal_font = QFont()
            normal_font.setBold(False)
            desc_lbl.setFont(normal_font)
            form.addRow(desc_lbl)

        for param in sec_def.params:
            current_value = ""
            if doc_section:
                current_value = doc_section.get(param.key)

            # Armadilha "sprite" vs "sff": alguns .def usam "sff" em vez de "sprite"
            if param.key == "sprite" and not current_value and doc_section:
                sff_val = doc_section.get("sff")
                if sff_val:
                    current_value = sff_val
                    self._sff_key_in_doc = "sff"
                else:
                    self._sff_key_in_doc = "sprite"

            if not current_value and param.default:
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

    def _create_param_widget(self, param, value: str, section_name: str) -> QWidget:
        from app.core.system_def import ParamType

        key_tuple = (section_name.lower(), param.key.lower())

        # Caso especial: versiondate
        if param.key == "versiondate":
            w = _DateWidget(value)
            w.changed.connect(lambda v, k=key_tuple: self._on_changed(k, v))
            self._widgets[key_tuple] = w
            return w

        # Caso especial: localcoord
        if param.key == "localcoord":
            w = _CoordWidget(value)
            w.changed.connect(lambda v, k=key_tuple: self._on_changed(k, v))
            self._widgets[key_tuple] = w
            return w

        if param.ptype == ParamType.BOOL:
            cb = QCheckBox()
            cb.setChecked(value.strip() not in ("0", "", "false", "no"))
            cb.stateChanged.connect(
                lambda state, k=key_tuple: self._on_changed(k, "1" if state else "0")
            )
            self._widgets[key_tuple] = cb
            return cb

        if param.ptype == ParamType.INT:
            sb = QSpinBox()
            sb.setRange(-9999999, 9999999)
            try:
                sb.setValue(int(value.strip().split(",")[0].strip()))
            except (ValueError, IndexError):
                sb.setValue(int(param.default) if param.default else 0)
            sb.valueChanged.connect(
                lambda v, k=key_tuple: self._on_changed(k, str(v))
            )
            self._widgets[key_tuple] = sb
            return sb

        if param.ptype == ParamType.ENUM:
            combo = QComboBox()
            for choice in param.choices:
                combo.addItem(choice)
            if value in param.choices:
                combo.setCurrentText(value)
            elif param.choices:
                combo.setCurrentText(param.choices[0])
            combo.currentTextChanged.connect(
                lambda t, k=key_tuple: self._on_changed(k, t)
            )
            self._widgets[key_tuple] = combo
            return combo

        if param.ptype == ParamType.FILE:
            row = _FileRow(value, self._char_dir)
            # Conecta reload de portrait se for o campo SFF
            if param.key in ("sprite", "sff"):
                row.changed.connect(self._on_sff_changed)
            row.changed.connect(lambda v, k=key_tuple: self._on_changed(k, v))
            self._widgets[key_tuple] = row
            return row

        # Default: STRING
        le = QLineEdit(value)
        le.textChanged.connect(
            lambda t, k=key_tuple: self._on_changed(k, t)
        )
        self._widgets[key_tuple] = le
        return le

    # ------------------------------------------------------------------
    # Slots de alteração
    # ------------------------------------------------------------------

    def _on_changed(self, key: tuple[str, str], value: str) -> None:
        if not self._loading:
            self._apply_change(key, value)

    def _apply_change(self, key: tuple[str, str], value: str) -> None:
        if self._doc is None:
            return
        section_name, param_key = key

        # Caso especial: "sprite" pode estar armazenado como "sff" no documento
        actual_key = param_key
        if section_name == "files" and param_key == "sprite":
            actual_key = self._sff_key_in_doc

        for sec in self._doc.sections:
            if sec.name.lower() == section_name:
                sec.set(actual_key, value)
                break

        self.changed.emit()

    @Slot(str)
    def _on_sff_changed(self, path: str) -> None:
        """Recarrega portrait quando o campo SFF muda."""
        self._update_file_status_panel()
        if path.strip():
            self._try_load_portrait()

    # ------------------------------------------------------------------
    # Status de arquivos
    # ------------------------------------------------------------------

    def _update_file_status_panel(self) -> None:
        if self._doc is None:
            return
        from app.core.char_def import KNOWN_SECTIONS
        from app.core.system_def import ParamType

        file_status: list[tuple[str, bool]] = []
        seen: set[str] = set()

        for sec_def in KNOWN_SECTIONS:
            doc_section = self._doc.section(sec_def.name)
            if doc_section is None:
                continue
            for param in sec_def.params:
                if param.ptype != ParamType.FILE:
                    continue
                val = doc_section.get(param.key)
                if not val:
                    continue
                dedup_key = f"{sec_def.name.lower()}:{val.lower()}"
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)
                full = os.path.join(self._char_dir, val) if not os.path.isabs(val) else val
                file_status.append((val, os.path.isfile(full)))

        self._portrait_panel.set_file_status(file_status)

    # ------------------------------------------------------------------
    # Carregamento do portrait
    # ------------------------------------------------------------------

    @Slot()
    def _try_load_portrait(self) -> None:
        if self._doc is None:
            self._portrait_panel.show_placeholder("Nenhum .def carregado")
            return

        doc_files = self._doc.section("Files")
        sff_val = ""
        if doc_files:
            sff_val = doc_files.get("sprite") or doc_files.get("sff") or ""

        if not sff_val:
            self._portrait_panel.show_placeholder("SFF não definido em [Files]")
            return

        sff_full = os.path.join(self._char_dir, sff_val) if not os.path.isabs(sff_val) else sff_val
        if not os.path.isfile(sff_full):
            self._portrait_panel.show_placeholder("SFF não encontrado:\n" + sff_val)
            return

        self._pending_sff_path = sff_full
        self._portrait_panel.show_placeholder("Carregando…")

        loader = _PortraitLoader(sff_full)
        loader.signals.finished.connect(self._on_portrait_loaded)
        loader.signals.error.connect(self._on_portrait_error)
        QThreadPool.globalInstance().start(loader)

    @Slot(object)
    def _on_portrait_loaded(self, sheet) -> None:
        # Guard de race condition: verifica se este ainda é o SFF esperado
        if sheet.path != self._pending_sff_path:
            return

        self._portrait_panel.set_sff_info(f"SFF v{sheet.version}")

        px_large: QPixmap | None = None
        px_small: QPixmap | None = None

        result = sheet.get_rgba(9000, 0)
        if result:
            rgba, w, h = result
            if w > 0 and h > 0:
                img = QImage(rgba, w, h, QImage.Format_RGBA8888)
                px_large = QPixmap.fromImage(img)

        result_s = sheet.get_rgba(9000, 1)
        if result_s:
            rgba, w, h = result_s
            if w > 0 and h > 0:
                img = QImage(rgba, w, h, QImage.Format_RGBA8888)
                px_small = QPixmap.fromImage(img)

        if px_large:
            self._portrait_panel.show_portrait(px_large, px_small)
        else:
            self._portrait_panel.show_placeholder("Portrait (9000,0) não encontrado")

    @Slot(str)
    def _on_portrait_error(self, msg: str) -> None:
        self._portrait_panel.show_placeholder(f"Erro ao carregar SFF:\n{msg}")

    # ------------------------------------------------------------------
    # Salvar
    # ------------------------------------------------------------------

    def save(self) -> None:
        if self._doc is None or not self._def_path:
            return
        self._doc.save(self._def_path)
