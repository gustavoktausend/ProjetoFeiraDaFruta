"""
QSyntaxHighlighter para arquivos .CNS e .CMD do MUGEN/Ikemen GO.

Regras de destaque:
  - Seções: [StateDef 200], [State 200, 0], [Command], etc.
  - Chaves conhecidas (type, value, trigger1, etc.)
  - Comentários (iniciados por ';')
  - Números (inteiros, floats, negativos)
  - Strings entre aspas
  - Palavras-chave de funções/operadores (ifelse, floor, ceil, etc.)
"""

from __future__ import annotations

from PySide6.QtCore import QRegularExpression, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextDocument,
)


def _fmt(color: str, bold: bool = False, italic: bool = False) -> QTextCharFormat:
    f = QTextCharFormat()
    f.setForeground(QColor(color))
    if bold:
        f.setFontWeight(QFont.Bold)
    if italic:
        f.setFontItalic(True)
    return f


# Paleta de cores (baseada em tema escuro)
_FORMATS = {
    "section":   _fmt("#569CD6", bold=True),   # Azul — [StateDef ...]
    "key":       _fmt("#9CDCFE"),              # Azul claro — type, value, trigger1
    "comment":   _fmt("#6A9955", italic=True), # Verde — ; comentário
    "number":    _fmt("#B5CEA8"),              # Verde claro — 123, -1.5
    "string":    _fmt("#CE9178"),              # Laranja — "texto"
    "keyword":   _fmt("#C586C0"),              # Roxo — ifelse, floor, ceil
    "operator":  _fmt("#D4D4D4"),              # Branco — =, +, -, *, /
    "state_val": _fmt("#DCDCAA"),              # Amarelo — valores de type=
}

# Expressões regulares
_RULES: list[tuple[QRegularExpression, str]] = [
    # Seção (deve vir antes de key/value)
    (QRegularExpression(r"^\s*\[[^\]]+\]"), "section"),
    # Comentário inline (após ;)
    (QRegularExpression(r";[^\n]*"), "comment"),
    # Strings entre aspas
    (QRegularExpression(r'"[^"]*"'), "string"),
    # Números (incluindo negativos e floats)
    (QRegularExpression(r"\b-?\d+(\.\d+)?\b"), "number"),
    # Chaves conhecidas (início de linha, antes do =)
    (QRegularExpression(r"^\s*(type|value|trigger\d*|triggerall|"
                        r"x|y|time|animtime|ctrl|facing|hitdef|"
                        r"hitflag|movetype|physics|statetype|"
                        r"velset|velmul|lifeadd|poweradd|"
                        r"name|command|guard\.dist|pausetime|"
                        r"sparkno|sparkxy|hitsound|guardsound|"
                        r"p1stateno|p2stateno|p1anim|p2anim|"
                        r"yaccel|ctrlturn|layerno|pos|scale|"
                        r"persistent|ignorehitpause|priority|"
                        r"movecancelrequired|slot)\s*(?==)", "key",
                        QRegularExpression.CaseInsensitiveOption),
    # Palavras-chave de expressão
    (QRegularExpression(
        r"\b(ifelse|floor|ceil|abs|cos|sin|log|exp|"
        r"random|numtarget|numenemy|numpartner|"
        r"life|lifemax|power|powermax|roundsexisted|"
        r"var|fvar|sysvar|sysfvar|teamside|p2dist|"
        r"palno|inguarddist|canrecover|alive|"
        r"ishelper|parentdist|root|parent|helper|"
        r"target|enemy|partner|playerid|"
        r"and|or|not|xor|true|false)\b",
        QRegularExpression.CaseInsensitiveOption,
    ), "keyword"),
]


class MugenHighlighter(QSyntaxHighlighter):
    """Realce de sintaxe para arquivos .CNS/.CMD do MUGEN."""

    def __init__(self, document: QTextDocument) -> None:
        super().__init__(document)
        self._rules = _RULES

    def highlightBlock(self, text: str) -> None:
        for pattern, fmt_name in self._rules:
            fmt = _FORMATS.get(fmt_name)
            if fmt is None:
                continue

            it = pattern.globalMatch(text)
            while it.hasNext():
                match = it.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)
