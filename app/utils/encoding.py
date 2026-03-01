"""
Detecção e tratamento de encoding para arquivos MUGEN/Ikemen GO.
Arquivos antigos usam latin-1 (cp1252), novos podem usar UTF-8.
"""

from __future__ import annotations

import chardet


def detect_encoding(path: str) -> str:
    """Detecta o encoding de um arquivo.

    Retorna 'utf-8', 'latin-1' ou outro codec detectado.
    Fallback para 'latin-1' se a detecção falhar (encoding mais comum em MUGEN).
    """
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except OSError:
        return "latin-1"

    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"

    result = chardet.detect(raw)
    encoding = result.get("encoding") or "latin-1"
    confidence = result.get("confidence") or 0.0

    if confidence < 0.6:
        return "latin-1"

    enc_lower = encoding.lower()
    if enc_lower in ("ascii", "utf-8"):
        return "utf-8"
    if enc_lower in ("windows-1252", "iso-8859-1", "iso-8859-2"):
        return "latin-1"

    return encoding


def read_text(path: str) -> tuple[str, str]:
    """Lê um arquivo de texto detectando o encoding.

    Retorna (conteúdo, encoding_usado).
    """
    encoding = detect_encoding(path)
    try:
        with open(path, "r", encoding=encoding, errors="replace") as f:
            content = f.read()
    except (OSError, LookupError):
        with open(path, "r", encoding="latin-1", errors="replace") as f:
            content = f.read()
        encoding = "latin-1"
    return content, encoding


def write_text(path: str, content: str, encoding: str = "utf-8") -> None:
    """Escreve um arquivo de texto com o encoding especificado."""
    with open(path, "w", encoding=encoding, newline="\n") as f:
        f.write(content)
