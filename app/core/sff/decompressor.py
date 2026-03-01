"""
Descompressores para os formatos de sprite do SFF v2 do Ikemen GO / MUGEN.

Formatos suportados:
  - raw (0): dados brutos sem compressão
  - RLE8 (2): Run-Length Encoding com paleta de 8 bits
  - RLE5 (3): RLE com paleta de 5 bits (indexado em 32 cores)
  - LZ5 (4): LZ77 simplificado com saída de 5 bits por símbolo
  - PNG (10/11/12): descompressão via Pillow
"""

from __future__ import annotations

import struct


def decompress(data: bytes, method: int, width: int, height: int) -> bytes:
    """Descomprime dados de sprite de acordo com o método.

    Retorna bytes raw (paleta de índices, 1 byte por pixel, row-major).
    """
    if method == 0:
        return _raw(data, width, height)
    if method == 2:
        return _rle8(data, width, height)
    if method == 3:
        return _rle5(data, width, height)
    if method == 4:
        return _lz5(data, width, height)
    if method in (10, 11, 12):
        return _png(data)
    raise ValueError(f"Método de compressão desconhecido: {method}")


# ------------------------------------------------------------------
# Raw
# ------------------------------------------------------------------

def _raw(data: bytes, width: int, height: int) -> bytes:
    expected = width * height
    if len(data) >= expected:
        return data[:expected]
    return data + bytes(expected - len(data))


# ------------------------------------------------------------------
# RLE8
# ------------------------------------------------------------------

def _rle8(data: bytes, width: int, height: int) -> bytes:
    """RLE8: sequências de (count, color_index)."""
    out = bytearray()
    i = 0
    n = len(data)
    target = width * height

    while i < n and len(out) < target:
        b = data[i]
        i += 1

        if b & 0x40:  # bit 6 set → run de pixels iguais
            count = (b & 0x3F) + 1
            if i >= n:
                break
            color = data[i]
            i += 1
            out.extend([color] * count)
        else:          # literal
            count = (b & 0x3F) + 1
            out.extend(data[i: i + count])
            i += count

    # Trunca/preenche até target
    if len(out) < target:
        out.extend(bytes(target - len(out)))
    return bytes(out[:target])


# ------------------------------------------------------------------
# RLE5
# ------------------------------------------------------------------

def _rle5(data: bytes, width: int, height: int) -> bytes:
    """RLE5: paleta de 32 cores (5 bits por pixel)."""
    out = bytearray()
    i = 0
    n = len(data)
    target = width * height

    while i < n and len(out) < target:
        b = data[i]
        i += 1

        if b & 0xC0 == 0x40:  # run
            count = (b & 0x3F) + 2
            if i >= n:
                break
            color = data[i] & 0x1F
            i += 1
            out.extend([color] * count)
        elif b & 0xC0 == 0x80:  # literal grande
            count = (b & 0x3F) + 1
            for _ in range(count):
                if i < n:
                    out.append(data[i] & 0x1F)
                    i += 1
        else:  # literal simples (1 pixel)
            out.append(b & 0x1F)

    if len(out) < target:
        out.extend(bytes(target - len(out)))
    return bytes(out[:target])


# ------------------------------------------------------------------
# LZ5
# ------------------------------------------------------------------

def _lz5(data: bytes, width: int, height: int) -> bytes:
    """LZ5: variante LZ77 usada no SFF v2 do MUGEN."""
    out = bytearray()
    i = 0
    n = len(data)
    target = width * height

    while i < n and len(out) < target:
        b = data[i]
        i += 1

        if b & 0x40:  # back-reference
            if i >= n:
                break
            b2 = data[i]
            i += 1
            length = (b & 0x3F) + 2
            offset = ((b2 & 0xFF) | ((b >> 6) << 8)) + 1
            start = max(0, len(out) - offset)
            for j in range(length):
                idx = start + j
                if idx < len(out):
                    out.append(out[idx])
                else:
                    out.append(0)
        else:  # literal
            count = (b & 0x3F) + 1
            out.extend(data[i: i + count])
            i += count

    if len(out) < target:
        out.extend(bytes(target - len(out)))
    return bytes(out[:target])


# ------------------------------------------------------------------
# PNG embutido (via Pillow)
# ------------------------------------------------------------------

def _png(data: bytes) -> bytes:
    """Descomprime PNG embutido retornando bytes RGBA."""
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(data))
        img = img.convert("RGBA")
        return img.tobytes()
    except Exception as exc:
        raise ValueError(f"Falha ao decodificar PNG embutido: {exc}") from exc
