"""
QAbstractListModel para a lista de personagens do select.def.
Suporta drag-and-drop (moveRows) para reordenação.
"""

from __future__ import annotations

from PySide6.QtCore import (
    QAbstractListModel,
    QByteArray,
    QMimeData,
    QModelIndex,
    Qt,
)

from app.core.select_def import CharEntry, SelectDefDocument


class RosterModel(QAbstractListModel):
    """Modelo de lista de personagens com suporte a drag-drop."""

    MIME_TYPE = "application/x-mugem-roster-rows"

    def __init__(self, doc: SelectDefDocument, parent=None) -> None:
        super().__init__(parent)
        self._doc = doc

    # ------------------------------------------------------------------
    # Interface básica do modelo
    # ------------------------------------------------------------------

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._doc.characters)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None
        entry = self._doc.characters[index.row()]

        if role == Qt.DisplayRole:
            return _display_name(entry)
        if role == Qt.ToolTipRole:
            return entry.to_line()
        if role == Qt.UserRole:
            return entry
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        default = super().flags(index)
        if index.isValid():
            return default | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled
        return default | Qt.ItemIsDropEnabled

    # ------------------------------------------------------------------
    # Drag-and-drop
    # ------------------------------------------------------------------

    def supportedDropActions(self) -> Qt.DropActions:
        return Qt.MoveAction

    def mimeTypes(self) -> list[str]:
        return [self.MIME_TYPE]

    def mimeData(self, indexes: list[QModelIndex]) -> QMimeData:
        mime = QMimeData()
        rows = sorted(set(i.row() for i in indexes if i.isValid()))
        data = QByteArray(",".join(str(r) for r in rows).encode())
        mime.setData(self.MIME_TYPE, data)
        return mime

    def dropMimeData(
        self,
        data: QMimeData,
        action: Qt.DropAction,
        row: int,
        column: int,
        parent: QModelIndex,
    ) -> bool:
        if not data.hasFormat(self.MIME_TYPE):
            return False
        raw = bytes(data.data(self.MIME_TYPE)).decode()
        source_rows = [int(r) for r in raw.split(",") if r.strip().isdigit()]
        if not source_rows:
            return False

        dest = row if row >= 0 else self.rowCount()

        # Executa o movimento (um de cada vez, ajustando índices)
        for i, src in enumerate(source_rows):
            adjusted_dest = dest - sum(s < dest for s in source_rows[:i])
            self._move_row(src - i, adjusted_dest)

        return True

    def _move_row(self, src: int, dest: int) -> None:
        if src == dest or src < 0 or dest < 0:
            return
        n = self.rowCount()
        if src >= n:
            return
        dest = min(dest, n)
        if dest > src:
            dest -= 1
        self.beginMoveRows(QModelIndex(), src, src, QModelIndex(), dest + (1 if dest >= src else 0))
        self._doc.move_character(src, dest)
        self.endMoveRows()

    # ------------------------------------------------------------------
    # Edição programática
    # ------------------------------------------------------------------

    def add_character(self, entry: CharEntry) -> None:
        row = self.rowCount()
        self.beginInsertRows(QModelIndex(), row, row)
        self._doc.characters.append(entry)
        self.endInsertRows()

    def remove_character(self, row: int) -> None:
        if 0 <= row < self.rowCount():
            self.beginRemoveRows(QModelIndex(), row, row)
            self._doc.remove_character(row)
            self.endRemoveRows()

    def entry_at(self, row: int) -> CharEntry | None:
        if 0 <= row < len(self._doc.characters):
            return self._doc.characters[row]
        return None

    def refresh(self) -> None:
        self.beginResetModel()
        self.endResetModel()


def _display_name(entry: CharEntry) -> str:
    if not entry.name:
        return "(linha vazia)"
    if entry.is_random:
        return "[random]"
    if entry.is_empty:
        return "[empty]"
    return entry.name
