"""
Decodificação de PCX (usado no SFF v1) via Pillow + fallback manual.
"""

from __future__ import annotations

import io
import struct


def pcx_to_rgba(
    pcx_data: bytes,
    shared_palette: list[tuple[int, int, int]] | None = None,
) -> tuple[bytes, int, int]:
    """Converte dados PCX em RGBA.

    Tenta usar Pillow primeiro; se falhar, usa decodificador manual.
    Retorna (bytes_rgba, width, height).
    """
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(pcx_data))

        if shared_palette and img.mode == "P":
            # Aplica paleta compartilhada
            flat = []
            for r, g, b in shared_palette:
                flat.extend([r, g, b])
            # Pillow espera 768 bytes para paleta RGB
            while len(flat) < 768:
                flat.append(0)
            img.putpalette(flat[:768])

        img = img.convert("RGBA")
        return img.tobytes(), img.width, img.height

    except Exception:
        return _decode_pcx_manual(pcx_data, shared_palette)


def _decode_pcx_manual(
    data: bytes,
    shared_palette: list[tuple[int, int, int]] | None,
) -> tuple[bytes, int, int]:
    """Decodificador PCX mínimo (8bpp, RLE)."""
    if len(data) < 128:
        return b"", 0, 0

    # Header PCX
    bpp = data[3]
    xmin = struct.unpack_from("<H", data, 4)[0]
    ymin = struct.unpack_from("<H", data, 6)[0]
    xmax = struct.unpack_from("<H", data, 8)[0]
    ymax = struct.unpack_from("<H", data, 10)[0]
    bytes_per_line = struct.unpack_from("<H", data, 66)[0]

    width = xmax - xmin + 1
    height = ymax - ymin + 1

    if width <= 0 or height <= 0 or bpp != 8:
        return b"", width, height

    # Extrai paleta
    palette = shared_palette
    if palette is None:
        palette = _extract_pcx_palette_local(data)
    if palette is None:
        palette = [(i, i, i) for i in range(256)]

    # Decomprime RLE
    pixels = _rle_decode_pcx(data[128:], bytes_per_line, height)

    # Converte índices em RGBA
    out = bytearray()
    for y in range(height):
        row_start = y * bytes_per_line
        for x in range(width):
            idx = pixels[row_start + x] if row_start + x < len(pixels) else 0
            r, g, b = palette[idx]
            # Índice 0 é transparente no MUGEN (convenção)
            a = 0 if idx == 0 else 255
            out.extend([r, g, b, a])

    return bytes(out), width, height


def _rle_decode_pcx(data: bytes, bytes_per_line: int, height: int) -> bytearray:
    out = bytearray()
    i = 0
    n = len(data)
    needed = bytes_per_line * height

    while i < n and len(out) < needed:
        b = data[i]
        i += 1
        if b >= 0xC0:
            count = b & 0x3F
            if i < n:
                color = data[i]
                i += 1
                out.extend([color] * count)
        else:
            out.append(b)

    return out


def _extract_pcx_palette_local(data: bytes) -> list[tuple[int, int, int]] | None:
    if len(data) < 769 or data[-769] != 0x0C:
        return None
    pal = data[-768:]
    return [(pal[i * 3], pal[i * 3 + 1], pal[i * 3 + 2]) for i in range(256)]
