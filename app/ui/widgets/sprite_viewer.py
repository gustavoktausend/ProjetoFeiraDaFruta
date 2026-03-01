"""
Visualizador de sprites SFF.

Layout:
  QSplitter (Horizontal)
    Esquerda: QTreeView (SpriteGroupModel)
    Direita:
      QLabel (informações do sprite)
      QGraphicsView (zoom/pan + grade de transparência)
"""

from __future__ import annotations

import os

from PySide6.QtCore import (
    QModelIndex,
    QRunnable,
    QThread,
    QThreadPool,
    Qt,
    Signal,
    Slot,
    QObject,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QImage,
    QPainter,
    QPixmap,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QFileDialog,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from app.core.project import IkemenProject
from app.core.sff.sff_reader import SpriteSheet
from app.ui.models.sprite_group_model import SpriteGroupModel


class _LoadSignals(QObject):
    finished = Signal(object)   # SpriteSheet | None
    error = Signal(str)


class _SffLoader(QRunnable):
    """Carrega SFF em background thread."""

    def __init__(self, path: str) -> None:
        super().__init__()
        self._path = path
        self.signals = _LoadSignals()

    def run(self) -> None:
        try:
            from app.core.sff.sff_reader import load
            sheet = load(self._path)
            self.signals.finished.emit(sheet)
        except Exception as exc:
            self.signals.error.emit(str(exc))


class ZoomableGraphicsView(QGraphicsView):
    """QGraphicsView com zoom via scroll e pan via click-drag."""

    def __init__(self, scene: QGraphicsScene, parent: QWidget | None = None) -> None:
        super().__init__(scene, parent)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setRenderHint(QPainter.Antialiasing, False)
        self.setRenderHint(QPainter.SmoothPixmapTransform, False)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self._scale_factor = 1.0

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y()
        if delta > 0:
            factor = 1.15
        else:
            factor = 1 / 1.15
        self._scale_factor *= factor
        self._scale_factor = max(0.1, min(self._scale_factor, 30.0))
        self.setTransform(
            self.transform().scale(factor, factor)
        )

    def reset_zoom(self) -> None:
        self.resetTransform()
        self._scale_factor = 1.0


class SpriteViewer(QWidget):
    """Painel de visualização de sprites SFF."""

    def __init__(self, project: IkemenProject, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._project = project
        self._sheet: SpriteSheet | None = None
        self._current_sff_path: str = ""

        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # Toolbar de abertura
        top_bar = QHBoxLayout()
        self._lbl_file = QLabel("Nenhum SFF carregado")
        self._lbl_file.setStyleSheet("color: #888;")
        btn_open = QPushButton("Abrir SFF…")
        btn_open.clicked.connect(self._browse_sff)
        top_bar.addWidget(self._lbl_file, 1)
        top_bar.addWidget(btn_open)
        main_layout.addLayout(top_bar)

        # Splitter principal
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter, 1)

        # Árvore de grupos/itens
        self._tree_model = SpriteGroupModel()
        self._tree = QTreeView()
        self._tree.setModel(self._tree_model)
        self._tree.setHeaderHidden(False)
        self._tree.setMinimumWidth(180)
        self._tree.selectionModel().currentChanged.connect(self._on_tree_selection)
        splitter.addWidget(self._tree)

        # Área direita
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 4, 4, 4)

        # Info
        self._lbl_info = QLabel("Selecione um sprite na árvore")
        self._lbl_info.setStyleSheet("color: #888; font-size: 11px;")
        right_layout.addWidget(self._lbl_info)

        # Controles de zoom
        zoom_row = QHBoxLayout()
        btn_zoom_in = QPushButton("+")
        btn_zoom_out = QPushButton("−")
        btn_zoom_reset = QPushButton("1:1")
        for btn in (btn_zoom_in, btn_zoom_out, btn_zoom_reset):
            btn.setFixedSize(36, 28)
        btn_zoom_in.clicked.connect(self._zoom_in)
        btn_zoom_out.clicked.connect(self._zoom_out)
        btn_zoom_reset.clicked.connect(self._zoom_reset)
        zoom_row.addWidget(btn_zoom_in)
        zoom_row.addWidget(btn_zoom_out)
        zoom_row.addWidget(btn_zoom_reset)
        zoom_row.addStretch()
        right_layout.addLayout(zoom_row)

        # GraphicsView
        self._scene = QGraphicsScene()
        self._gv = ZoomableGraphicsView(self._scene)
        self._gv.setBackgroundBrush(_checkerboard_brush())
        right_layout.addWidget(self._gv, 1)

        splitter.addWidget(right)
        splitter.setSizes([200, 600])

        # Status de carregamento
        self._lbl_status = QLabel("")
        main_layout.addWidget(self._lbl_status)

    # ------------------------------------------------------------------
    # Abertura de arquivo
    # ------------------------------------------------------------------

    @Slot()
    def _browse_sff(self) -> None:
        root = self._project.root
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir arquivo SFF", root, "SFF Files (*.sff)"
        )
        if path:
            self.load_sff(path)

    def load_sff(self, path: str) -> None:
        self._current_sff_path = path
        self._lbl_file.setText(os.path.basename(path))
        self._lbl_status.setText("Carregando…")
        self._scene.clear()
        self._tree_model.set_sheet(None)

        loader = _SffLoader(path)
        loader.signals.finished.connect(self._on_sheet_loaded)
        loader.signals.error.connect(self._on_load_error)
        QThreadPool.globalInstance().start(loader)

    @Slot(object)
    def _on_sheet_loaded(self, sheet: SpriteSheet) -> None:
        self._sheet = sheet
        self._tree_model.set_sheet(sheet)
        self._tree.expandToDepth(0)
        self._lbl_status.setText(
            f"SFF v{sheet.version} — {sheet.count()} sprites carregados"
        )

    @Slot(str)
    def _on_load_error(self, msg: str) -> None:
        self._lbl_status.setText(f"Erro: {msg}")

    # ------------------------------------------------------------------
    # Seleção na árvore
    # ------------------------------------------------------------------

    @Slot(QModelIndex, QModelIndex)
    def _on_tree_selection(self, current: QModelIndex, _prev: QModelIndex) -> None:
        data = self._tree_model.data(current, Qt.UserRole)
        if data is None:
            return
        group, item = data
        if item is None:
            return  # Clicou em grupo

        self._display_sprite(group, item)

    def _display_sprite(self, group: int, item: int) -> None:
        if self._sheet is None:
            return

        result = self._sheet.get_rgba(group, item)
        if result is None:
            self._lbl_info.setText(f"Grupo {group}, Item {item} — dados indisponíveis")
            self._scene.clear()
            return

        rgba, w, h = result
        if w == 0 or h == 0:
            self._lbl_info.setText(f"Grupo {group}, Item {item} — sprite vazio")
            self._scene.clear()
            return

        spr_info = self._sheet.sprite_info(group, item)
        x_off = getattr(spr_info, "x", 0)
        y_off = getattr(spr_info, "y", 0)
        fmt = getattr(spr_info, "fmt", "?")

        self._lbl_info.setText(
            f"Grupo {group}, Item {item}  —  {w}×{h} px  "
            f"(offset: {x_off},{y_off})  formato: {fmt}"
        )

        img = QImage(rgba, w, h, QImage.Format_RGBA8888)
        pixmap = QPixmap.fromImage(img)
        self._scene.clear()
        self._scene.addPixmap(pixmap)
        self._scene.setSceneRect(0, 0, w, h)
        self._gv.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)

    # ------------------------------------------------------------------
    # Zoom
    # ------------------------------------------------------------------

    def _zoom_in(self) -> None:
        self._gv.scale(1.2, 1.2)

    def _zoom_out(self) -> None:
        self._gv.scale(1 / 1.2, 1 / 1.2)

    def _zoom_reset(self) -> None:
        self._gv.reset_zoom()


# ------------------------------------------------------------------
# Grade de transparência (xadrez)
# ------------------------------------------------------------------

def _checkerboard_brush(size: int = 8) -> QBrush:
    """Cria um QBrush com padrão xadrez para fundo transparente."""
    pixmap = QPixmap(size * 2, size * 2)
    pixmap.fill(QColor(180, 180, 180))
    painter = QPainter(pixmap)
    painter.fillRect(0, 0, size, size, QColor(220, 220, 220))
    painter.fillRect(size, size, size, size, QColor(220, 220, 220))
    painter.end()
    return QBrush(pixmap)
