"""
Parser/writer round-trip para o formato INI-like do MUGEN/Ikemen GO.

Diferenças críticas do configparser padrão:
- Seções duplicadas (ex: múltiplos [Command] em .CMD)
- Comentários inline após ';' são preservados
- Linhas vazias entre blocos são preservadas
- Seções com nomes complexos: [StateDef 200], [State 200, 0]
- Chaves sem valor (bare keys)
- Suporte a continuação de linha com '\'
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterator


@dataclass
class IniEntry:
    """Uma entrada chave=valor dentro de uma seção."""
    key: str
    value: str
    comment: str = ""      # comentário inline (incluindo ';')
    raw_line: str = ""     # linha original completa

    def to_line(self) -> str:
        if self.raw_line and not self._was_modified():
            return self.raw_line
        line = f"{self.key} = {self.value}"
        if self.comment:
            line = f"{line}  {self.comment}"
        return line

    def _was_modified(self) -> bool:
        # Checa se key ou value diferem do que estava no raw_line
        stripped = self.raw_line.strip()
        eq_idx = stripped.find("=")
        if eq_idx == -1:
            return self.value != ""
        orig_key = stripped[:eq_idx].strip()
        rest = stripped[eq_idx + 1:]
        comment_idx = rest.find(";")
        if comment_idx != -1:
            orig_value = rest[:comment_idx].strip()
        else:
            orig_value = rest.strip()
        return orig_key != self.key or orig_value != self.value


@dataclass
class IniSection:
    """Uma seção do arquivo INI (pode haver seções com mesmo nome)."""
    name: str
    entries: list[IniEntry] = field(default_factory=list)
    # Linhas de overhead (comentários, vazias) ANTES da linha [secao]
    header_lines: list[str] = field(default_factory=list)
    # Linha original do cabeçalho [secao]
    header_raw: str = ""

    def get(self, key: str, default: str = "") -> str:
        """Retorna o valor de uma chave (case-insensitive)."""
        key_lower = key.lower()
        for entry in self.entries:
            if entry.key.lower() == key_lower:
                return entry.value
        return default

    def set(self, key: str, value: str) -> None:
        """Define ou atualiza o valor de uma chave."""
        key_lower = key.lower()
        for entry in self.entries:
            if entry.key.lower() == key_lower:
                entry.value = value
                return
        self.entries.append(IniEntry(key=key, value=value))

    def keys(self) -> list[str]:
        return [e.key for e in self.entries]

    def items(self) -> list[tuple[str, str]]:
        return [(e.key, e.value) for e in self.entries]

    def to_lines(self) -> list[str]:
        lines: list[str] = []
        lines.extend(self.header_lines)
        lines.append(self.header_raw if self.header_raw else f"[{self.name}]")
        for entry in self.entries:
            lines.append(entry.to_line())
        return lines


class MugenIniDocument:
    """Documento INI completo com preservação de ordem e comentários."""

    def __init__(self) -> None:
        self.sections: list[IniSection] = []
        # Linhas que ficam antes de qualquer seção (cabeçalho do arquivo)
        self.preamble: list[str] = []
        # Linhas após a última seção
        self.epilogue: list[str] = []
        self._encoding: str = "utf-8"

    # ------------------------------------------------------------------
    # Acesso por nome de seção (retorna primeiro match)
    # ------------------------------------------------------------------

    def section(self, name: str) -> IniSection | None:
        name_lower = name.lower()
        for s in self.sections:
            if s.name.lower() == name_lower:
                return s
        return None

    def sections_named(self, name: str) -> list[IniSection]:
        name_lower = name.lower()
        return [s for s in self.sections if s.name.lower() == name_lower]

    def get(self, section: str, key: str, default: str = "") -> str:
        sec = self.section(section)
        if sec is None:
            return default
        return sec.get(key, default)

    def set(self, section: str, key: str, value: str) -> None:
        sec = self.section(section)
        if sec is None:
            sec = IniSection(name=section)
            self.sections.append(sec)
        sec.set(key, value)

    def iter_sections(self) -> Iterator[IniSection]:
        yield from self.sections

    # ------------------------------------------------------------------
    # Serialização
    # ------------------------------------------------------------------

    def to_text(self) -> str:
        lines: list[str] = []
        lines.extend(self.preamble)
        for sec in self.sections:
            lines.extend(sec.to_lines())
        lines.extend(self.epilogue)
        return "\n".join(lines)

    def save(self, path: str) -> None:
        from app.utils.encoding import write_text
        write_text(path, self.to_text(), self._encoding)


# ------------------------------------------------------------------
# Parser
# ------------------------------------------------------------------

_RE_SECTION = re.compile(r"^\[([^\]]+)\]")
_RE_KEYVAL = re.compile(r"^([^=;]+?)\s*=\s*(.*)")
_RE_COMMENT = re.compile(r"^[;,]")


def load(path: str) -> MugenIniDocument:
    """Carrega e parseia um arquivo INI-like do MUGEN."""
    from app.utils.encoding import read_text

    content, encoding = read_text(path)
    doc = _parse_text(content)
    doc._encoding = encoding
    return doc


def loads(text: str) -> MugenIniDocument:
    """Parseia texto INI-like do MUGEN diretamente de uma string."""
    return _parse_text(text)


def _parse_text(text: str) -> MugenIniDocument:
    doc = MugenIniDocument()
    current_section: IniSection | None = None
    pending_lines: list[str] = []   # linhas (comentários/vazias) pendentes
    first_section_seen: bool = False

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()

        # Linha vazia
        if not stripped:
            pending_lines.append(raw)
            i += 1
            continue

        # Linha de comentário puro
        if _RE_COMMENT.match(stripped):
            pending_lines.append(raw)
            i += 1
            continue

        # Cabeçalho de seção
        m_sec = _RE_SECTION.match(stripped)
        if m_sec:
            sec_name = m_sec.group(1).strip()
            sec = IniSection(name=sec_name, header_raw=raw)
            if not first_section_seen:
                # Linhas pendentes antes da primeira seção → preamble
                doc.preamble.extend(pending_lines)
                sec.header_lines = []
            else:
                sec.header_lines = pending_lines
            pending_lines = []
            first_section_seen = True
            doc.sections.append(sec)
            current_section = sec
            i += 1
            continue

        # Chave = Valor
        m_kv = _RE_KEYVAL.match(stripped)
        if m_kv and current_section is not None:
            key = m_kv.group(1).strip()
            rest = m_kv.group(2)
            # Separar comentário inline
            value, inline_comment = _split_inline_comment(rest)
            # Continuação de linha com '\'
            while value.endswith("\\") and i + 1 < len(lines):
                value = value[:-1].rstrip()
                i += 1
                next_stripped = lines[i].strip()
                next_val, next_comment = _split_inline_comment(next_stripped)
                value += " " + next_val
                if next_comment:
                    inline_comment = next_comment
            if pending_lines:
                # Linhas de overhead dentro da seção viraram entries de comentário
                for pl in pending_lines:
                    current_section.entries.append(
                        IniEntry(key="", value="", raw_line=pl)
                    )
                pending_lines = []
            entry = IniEntry(
                key=key,
                value=value.strip(),
                comment=inline_comment,
                raw_line=raw,
            )
            current_section.entries.append(entry)
            i += 1
            continue

        # Linha sem '=' dentro de uma seção (bare key ou linha especial)
        if current_section is not None:
            if pending_lines:
                for pl in pending_lines:
                    current_section.entries.append(
                        IniEntry(key="", value="", raw_line=pl)
                    )
                pending_lines = []
            current_section.entries.append(
                IniEntry(key="", value="", raw_line=raw)
            )
            i += 1
            continue

        # Antes de qualquer seção
        if current_section is None:
            if pending_lines:
                doc.preamble.extend(pending_lines)
                pending_lines = []
            doc.preamble.append(raw)
            i += 1
            continue

        pending_lines.append(raw)
        i += 1

    # Linhas pendentes ao final
    if pending_lines:
        if current_section is not None:
            doc.epilogue.extend(pending_lines)
        else:
            doc.preamble.extend(pending_lines)

    return doc


def _split_inline_comment(text: str) -> tuple[str, str]:
    """Separa valor de comentário inline.

    Exemplo: 'KFM, stages/kfm.def  ; personagem padrão'
             → ('KFM, stages/kfm.def', '; personagem padrão')
    """
    # Procura ';' que não está dentro de aspas
    in_quote = False
    quote_char = ""
    for idx, ch in enumerate(text):
        if ch in ('"', "'") and not in_quote:
            in_quote = True
            quote_char = ch
        elif in_quote and ch == quote_char:
            in_quote = False
        elif ch == ";" and not in_quote:
            value = text[:idx].rstrip()
            comment = text[idx:].strip()
            return value, comment
    return text.strip(), ""
