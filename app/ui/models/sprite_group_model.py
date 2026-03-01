"""
QAbstractItemModel para a árvore de sprites (Grupo → Item).

Estrutura:
  Root
    Grupo 0
      Item 0
      Item 1
      ...
    Grupo 1
      ...
"""

from __future__ import annotations

from PySide6.QtCore import (
    QAbstractItemModel,
    QModelIndex,
    Qt,
)

from app.core.sff.sff_reader import SpriteSheet


class SpriteGroupModel(QAbstractItemModel):
    """Modelo de árvore para navegação de sprites por grupo/item."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._sheet: SpriteSheet | None = None
        self._groups: list[int] = []
        self._items: dict[int, list[int]] = {}   # group → [item, ...]

    def set_sheet(self, sheet: SpriteSheet | None) -> None:
        self.beginResetModel()
        self._sheet = sheet
        if sheet is None:
            self._groups = []
            self._items = {}
        else:
            self._groups = sheet.groups()
            self._items = {g: sheet.items_in_group(g) for g in self._groups}
        self.endResetModel()

    # ------------------------------------------------------------------
    # Interface do modelo
    # ------------------------------------------------------------------

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if not parent.isValid():
            # Raiz: número de grupos
            return len(self._groups)
        if parent.internalPointer() is None:
            # Nó de grupo
            group = self._groups[parent.row()]
            return len(self._items.get(group, []))
        # Nó de item: sem filhos
        return 0

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 1

    def index(self, row: int, column: int, parent: QModelIndex = QModelIndex()) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            # Filho da raiz = nó de grupo
            return self.createIndex(row, column, None)

        # Filho de grupo = nó de item
        group_row = parent.row()
        return self.createIndex(row, column, group_row)

    def parent(self, index: QModelIndex) -> QModelIndex:
        if not index.isValid():
            return QModelIndex()

        ptr = index.internalPointer()
        if ptr is None:
            # É um nó de grupo → pai é raiz
            return QModelIndex()

        # É um nó de item → pai é o nó de grupo
        group_row = ptr  # ptr guarda o índice do grupo
        return self.createIndex(group_row, 0, None)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None

        ptr = index.internalPointer()

        if role == Qt.DisplayRole:
            if ptr is None:
                # Nó de grupo
                g = self._groups[index.row()]
                count = len(self._items.get(g, []))
                return f"Grupo {g}  ({count} sprites)"
            else:
                # Nó de item
                group_row = ptr
                group = self._groups[group_row]
                items = self._items.get(group, [])
                if index.row() < len(items):
                    item = items[index.row()]
                    return f"Item {item}"

        if role == Qt.UserRole:
            # Retorna (group, item) para itens, (group, None) para grupos
            if ptr is None:
                return (self._groups[index.row()], None)
            else:
                group_row = ptr
                group = self._groups[group_row]
                items = self._items.get(group, [])
                if index.row() < len(items):
                    return (group, items[index.row()])

        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.NoItemFlags
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return "Sprites"
        return None
