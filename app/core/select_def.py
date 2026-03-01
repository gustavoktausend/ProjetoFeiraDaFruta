"""
Parser para o arquivo select.def do Ikemen GO / MUGEN.

Formato especial da seção [Characters]:
  charname, stagepath, music=arq.mp3, includestage=1

Cada linha não é um par chave=valor simples; é uma lista CSV onde:
  - Campo 0: nome do personagem (ou 'random', 'empty')
  - Campo 1: caminho da stage (opcional)
  - Campos seguintes: opções no formato chave=valor
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Iterator

from app.utils.encoding import read_text, write_text


@dataclass
class CharEntry:
    """Uma entrada de personagem no select.def."""
    name: str                         # Nome/caminho do personagem
    stage: str = ""                   # Stage associada
    options: dict[str, str] = field(default_factory=dict)
    comment: str = ""                 # Comentário inline (com ';')
    raw_line: str = ""                # Linha original para round-trip

    def to_line(self) -> str:
        parts = [self.name]
        if self.stage:
            parts.append(self.stage)
        for k, v in self.options.items():
            parts.append(f"{k}={v}")
        line = ", ".join(parts)
        if self.comment:
            line = f"{line}  {self.comment}"
        return line

    @property
    def is_random(self) -> bool:
        return self.name.lower() == "random"

    @property
    def is_empty(self) -> bool:
        return self.name.lower() in ("empty", "")


@dataclass
class ExtraStageEntry:
    """Uma entrada de stage extra no select.def ([ExtraStages])."""
    path: str
    comment: str = ""
    raw_line: str = ""

    def to_line(self) -> str:
        line = self.path
        if self.comment:
            line = f"{line}  {self.comment}"
        return line


class SelectDefDocument:
    """Representa o conteúdo completo do select.def."""

    def __init__(self) -> None:
        self.characters: list[CharEntry] = []
        self.extra_stages: list[ExtraStageEntry] = []
        # Linhas brutas de outras seções não parseadas
        self._raw_other: list[str] = []
        # Preamble (antes de [Characters])
        self._preamble: list[str] = []
        # Linhas entre [Characters] e [ExtraStages]
        self._inter: list[str] = []
        # Linhas após [ExtraStages]
        self._epilogue: list[str] = []
        self._path: str = ""
        self._encoding: str = "utf-8"

    def add_character(self, name: str, stage: str = "", **opts: str) -> None:
        self.characters.append(
            CharEntry(name=name, stage=stage, options=dict(opts))
        )

    def remove_character(self, index: int) -> None:
        if 0 <= index < len(self.characters):
            del self.characters[index]

    def move_character(self, from_idx: int, to_idx: int) -> None:
        if from_idx == to_idx:
            return
        chars = self.characters
        item = chars.pop(from_idx)
        chars.insert(to_idx, item)

    def to_text(self) -> str:
        lines: list[str] = []
        lines.extend(self._preamble)
        lines.append("[Characters]")
        for entry in self.characters:
            lines.append(entry.to_line())
        lines.extend(self._inter)
        if self.extra_stages:
            lines.append("[ExtraStages]")
            for es in self.extra_stages:
                lines.append(es.to_line())
        lines.extend(self._epilogue)
        return "\n".join(lines)

    def save(self, path: str | None = None) -> None:
        target = path or self._path
        write_text(target, self.to_text(), self._encoding)

    def iter_characters(self) -> Iterator[CharEntry]:
        yield from self.characters


# ------------------------------------------------------------------
# Parser
# ------------------------------------------------------------------

_RE_COMMENT = re.compile(r"^[;,]")


def load(path: str) -> SelectDefDocument:
    content, encoding = read_text(path)
    doc = _parse_text(content)
    doc._path = path
    doc._encoding = encoding
    return doc


def loads(text: str) -> SelectDefDocument:
    return _parse_text(text)


def _parse_text(text: str) -> SelectDefDocument:
    doc = SelectDefDocument()
    lines = text.splitlines()

    # Estado da máquina de estados
    MODE_PREAMBLE = "preamble"
    MODE_CHARACTERS = "characters"
    MODE_INTER = "inter"
    MODE_EXTRA = "extra"
    MODE_OTHER = "other"

    mode = MODE_PREAMBLE

    for raw in lines:
        stripped = raw.strip()

        # Cabeçalhos de seção
        if stripped.lower() == "[characters]":
            mode = MODE_CHARACTERS
            continue
        if stripped.lower() == "[extrastages]":
            if mode == MODE_CHARACTERS:
                mode = MODE_INTER
                doc._inter = []
            mode = MODE_EXTRA
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            mode = MODE_OTHER
            doc._raw_other.append(raw)
            continue

        # Linha vazia ou comentário
        if not stripped or _RE_COMMENT.match(stripped):
            if mode == MODE_PREAMBLE:
                doc._preamble.append(raw)
            elif mode == MODE_CHARACTERS:
                doc.characters.append(
                    CharEntry(name="", raw_line=raw)
                )
            elif mode in (MODE_INTER, MODE_EXTRA):
                doc._inter.append(raw)
            elif mode == MODE_OTHER:
                doc._raw_other.append(raw)
            continue

        if mode == MODE_PREAMBLE:
            doc._preamble.append(raw)

        elif mode == MODE_CHARACTERS:
            entry = _parse_char_line(raw)
            doc.characters.append(entry)

        elif mode == MODE_INTER:
            doc._inter.append(raw)

        elif mode == MODE_EXTRA:
            # Remove comentário inline
            semicolon = stripped.find(";")
            comment = ""
            if semicolon != -1:
                comment = stripped[semicolon:]
                path_str = stripped[:semicolon].strip()
            else:
                path_str = stripped
            doc.extra_stages.append(
                ExtraStageEntry(path=path_str, comment=comment, raw_line=raw)
            )

        elif mode == MODE_OTHER:
            doc._raw_other.append(raw)

    return doc


def _parse_char_line(raw: str) -> CharEntry:
    """Parseia uma linha da seção [Characters]."""
    stripped = raw.strip()

    # Separa comentário inline
    semicolon = stripped.find(";")
    comment = ""
    if semicolon != -1:
        comment = stripped[semicolon:].strip()
        main_part = stripped[:semicolon].strip()
    else:
        main_part = stripped

    # Divide por vírgula
    parts = [p.strip() for p in main_part.split(",")]

    if not parts or not parts[0]:
        return CharEntry(name="", comment=comment, raw_line=raw)

    name = parts[0]
    stage = ""
    options: dict[str, str] = {}

    for part in parts[1:]:
        part = part.strip()
        if "=" in part:
            k, _, v = part.partition("=")
            options[k.strip().lower()] = v.strip()
        elif part:
            stage = part

    return CharEntry(
        name=name,
        stage=stage,
        options=options,
        comment=comment,
        raw_line=raw,
    )
