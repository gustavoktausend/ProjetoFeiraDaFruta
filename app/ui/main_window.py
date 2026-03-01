"""
Janela principal do MugemUI.

Estrutura:
  QMainWindow
    ├── QToolBar  (Abrir, Salvar Tudo, Separador, Sobre)
    ├── QTabWidget central
    │    ├── Tab "Início"          → WelcomePanel
    │    ├── Tab "system.def"      → SystemDefEditor  (abre com projeto)
    │    ├── Tab "Roster"          → RosterEditor
    │    ├── Tab "Personagem"      → CharacterEditor
    │    └── Tab "Sprites"         → SpriteViewer
    └── QStatusBar
"""

from __future__ import annotations

import os

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QWidget,
)

from app.core.project import IkemenProject, ProjectError
from app.ui.widgets.welcome_panel import WelcomePanel


class MainWindow(QMainWindow):
    project_opened = Signal(object)   # emite IkemenProject

    def __init__(self) -> None:
        super().__init__()
        self._project: IkemenProject | None = None
        self._dirty: bool = False

        self.setWindowTitle("MugemUI — Ikemen GO Editor")
        self.resize(1200, 780)

        self._build_toolbar()
        self._build_tabs()
        self._build_statusbar()

    # ------------------------------------------------------------------
    # Construção da UI
    # ------------------------------------------------------------------

    def _build_toolbar(self) -> None:
        tb = QToolBar("Principal", self)
        tb.setMovable(False)
        self.addToolBar(tb)

        self._act_open = QAction("Abrir Projeto…", self)
        self._act_open.setShortcut(QKeySequence.Open)
        self._act_open.setStatusTip("Abre a pasta raiz de um projeto Ikemen GO")
        self._act_open.triggered.connect(self._on_open)
        tb.addAction(self._act_open)

        self._act_save = QAction("Salvar Tudo", self)
        self._act_save.setShortcut(QKeySequence.Save)
        self._act_save.setStatusTip("Salva todas as alterações pendentes")
        self._act_save.setEnabled(False)
        self._act_save.triggered.connect(self._on_save_all)
        tb.addAction(self._act_save)

        tb.addSeparator()

        act_about = QAction("Sobre", self)
        act_about.triggered.connect(self._on_about)
        tb.addAction(act_about)

    def _build_tabs(self) -> None:
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        self.setCentralWidget(self._tabs)

        self._welcome = WelcomePanel()
        self._welcome.open_requested.connect(self._on_open)
        self._tabs.addTab(self._welcome, "Início")

        # Os demais tabs são criados sob demanda (lazy) ao abrir projeto
        self._tab_system: QWidget | None = None
        self._tab_roster: QWidget | None = None
        self._tab_character: QWidget | None = None
        self._tab_sprites: QWidget | None = None

    def _build_statusbar(self) -> None:
        sb = QStatusBar()
        self.setStatusBar(sb)
        self._statusbar = sb
        sb.showMessage("Bem-vindo ao MugemUI. Abra um projeto para começar.")

    # ------------------------------------------------------------------
    # Ações
    # ------------------------------------------------------------------

    @Slot()
    def _on_open(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "Selecione a pasta raiz do projeto Ikemen GO",
            os.path.expanduser("~"),
        )
        if not path:
            return
        self._load_project(path)

    def _load_project(self, path: str) -> None:
        try:
            project = IkemenProject.open(path)
        except ProjectError as exc:
            QMessageBox.critical(self, "Erro ao Abrir Projeto", str(exc))
            return

        self._project = project
        self._dirty = False
        self._update_title()
        self._statusbar.showMessage(f"Projeto '{project.name}' carregado.")
        self._act_save.setEnabled(True)
        self._open_project_tabs(project)
        self.project_opened.emit(project)

    def _open_project_tabs(self, project: IkemenProject) -> None:
        """Cria (ou recria) as abas específicas do projeto."""
        # Importações locais para não retardar inicialização
        from app.ui.widgets.system_def_editor import SystemDefEditor
        from app.ui.widgets.roster_editor import RosterEditor
        from app.ui.widgets.character_editor import CharacterEditor
        from app.ui.widgets.sprite_viewer import SpriteViewer

        # Remove abas de projeto anteriores (índices > 0)
        while self._tabs.count() > 1:
            self._tabs.removeTab(1)

        # system.def
        if project.system_def:
            editor = SystemDefEditor(project)
            editor.changed.connect(self._mark_dirty)
            self._tabs.addTab(editor, "system.def")
            self._tab_system = editor

        # Roster
        if project.select_def:
            roster = RosterEditor(project)
            roster.changed.connect(self._mark_dirty)
            self._tabs.addTab(roster, "Roster")
            self._tab_roster = roster

        # Personagem
        char_ed = CharacterEditor(project)
        char_ed.changed.connect(self._mark_dirty)
        self._tabs.addTab(char_ed, "Personagem")
        self._tab_character = char_ed

        # Sprites
        sprite_v = SpriteViewer(project)
        self._tabs.addTab(sprite_v, "Sprites")
        self._tab_sprites = sprite_v

        self._tabs.setCurrentIndex(1)  # Vai direto para system.def

    @Slot()
    def _on_save_all(self) -> None:
        if self._project is None:
            return
        saved_any = False

        if self._tab_system is not None:
            from app.ui.widgets.system_def_editor import SystemDefEditor
            if isinstance(self._tab_system, SystemDefEditor):
                self._tab_system.save()
                saved_any = True

        if self._tab_roster is not None:
            from app.ui.widgets.roster_editor import RosterEditor
            if isinstance(self._tab_roster, RosterEditor):
                self._tab_roster.save()
                saved_any = True

        if self._tab_character is not None:
            from app.ui.widgets.character_editor import CharacterEditor
            if isinstance(self._tab_character, CharacterEditor):
                self._tab_character.save()
                saved_any = True

        if saved_any:
            self._dirty = False
            self._update_title()
            self._statusbar.showMessage("Todas as alterações foram salvas.")

    @Slot()
    def _on_about(self) -> None:
        QMessageBox.about(
            self,
            "Sobre MugemUI",
            "<h3>MugemUI 0.1.0</h3>"
            "<p>Editor gráfico para projetos <b>Ikemen GO</b> / MUGEN.</p>"
            "<p>Desenvolvido com Python + PySide6.</p>",
        )

    # ------------------------------------------------------------------
    # Estado dirty
    # ------------------------------------------------------------------

    @Slot()
    def _mark_dirty(self) -> None:
        if not self._dirty:
            self._dirty = True
            self._update_title()

    def _update_title(self) -> None:
        base = "MugemUI"
        if self._project:
            base = f"MugemUI — {self._project.name}"
        if self._dirty:
            base = f"*{base}"
        self.setWindowTitle(base)

    # ------------------------------------------------------------------
    # Fechar janela
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if self._dirty:
            reply = QMessageBox.question(
                self,
                "Alterações não salvas",
                "Há alterações não salvas. Deseja salvar antes de sair?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            )
            if reply == QMessageBox.Save:
                self._on_save_all()
                event.accept()
            elif reply == QMessageBox.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
