"""
Leitor do formato SFF v2 do Ikemen GO / MUGEN.

Header principal (544 bytes):
  Offset  Tamanho  Descrição
  0       12       Assinatura "ElecbyteSpr\0"
  12      1        verlo3
  13      1        verlo2
  14      1        verlo1
  15      1        verhi (deve ser 2)
  16      4        reserved1
  20      4        reserved2
  24      4        compatverlo3, compatverlo2, compatverlo1, compatverhi
  28      4        Offset do array de paletas (ldataoffset)
  32      4        Comprimento do array de paletas
  36      4        Offset do ldata (sprite data block)
  40      4        Comprimento do ldata
  44      4        Offset do tdata (sprite thumbnail data)
  48      4        Comprimento do tdata
  52      4        reserved3
  56      4        Número de sprites (nsprites)
  60      4        Offset do array de sprites (imagesoffset)
  64      4        Número de paletas
  68      4        Offset do array de paletas (separado de ldataoffset)
  ...

Sprite node (28 bytes a partir de imagesoffset):
  Offset  Tamanho  Descrição
  0       2        Group number
  2       2        Image number
  4       2        Width
  6       2        Height
  8       2        X (signed)
  10      2        Y (signed)
  12      2        Linked index (0xFFFF = sem link)
  14      1        Flags
  15      1        Format (compression method)
  16      4        Color depth (palette index)
  20      4        Data offset (relativo ao início do ldata/tdata)
  24      4        Data length
  28      (fim)

Paleta node (16 bytes):
  0       2        Group
  2       2        Item
  4       4        Number of colors
  8       4        Linked index
  12      4        Data offset (relativo ao ldataoffset)
  16      (fim)... mas cada paleta tem 1024 bytes de dados (256 × RGBA)
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


@dataclass
class PaletteInfoV2:
    group: int
    item: int
    num_colors: int
    linked_index: int
    data_offset: int   # Absoluto no arquivo
    colors: list[tuple[int, int, int, int]] = field(default_factory=list)


@dataclass
class SpriteInfoV2:
    """Informação de um sprite SFF v2."""
    group: int
    item: int
    width: int
    height: int
    x: int
    y: int
    linked_index: int       # 0xFFFF = sem link
    flags: int
    fmt: int                # Método de compressão
    palette_index: int
    data_offset: int        # Absoluto no arquivo (já calculado)
    data_length: int
    use_tdata: bool         # True se usar tdata em vez de ldata
    _pixels_cache: bytes | None = field(default=None, repr=False)

    @property
    def is_linked(self) -> bool:
        return self.linked_index != 0xFFFF and self.linked_index != 0

    def to_rgba(
        self,
        raw_data: bytes,
        palette: list[tuple[int, int, int, int]] | None,
    ) -> tuple[bytes, int, int]:
        """Converte dados brutos em pixels RGBA.

        Retorna (bytes_rgba, width, height).
        """
        if self._pixels_cache is not None:
            return self._pixels_cache, self.width, self.height

        from app.core.sff.decompressor import decompress

        # PNG embutido (formatos 10, 11, 12) já retornam RGBA diretamente
        if self.fmt in (10, 11, 12):
            try:
                rgba = decompress(raw_data, self.fmt, self.width, self.height)
                self._pixels_cache = rgba
                return rgba, self.width, self.height
            except Exception:
                return _blank_rgba(self.width, self.height), self.width, self.height

        # Outros formatos: descomprime para índices de paleta
        try:
            indices = decompress(raw_data, self.fmt, self.width, self.height)
        except Exception:
            return _blank_rgba(self.width, self.height), self.width, self.height

        if palette:
            rgba = _indices_to_rgba(indices, palette)
        else:
            # Sem paleta: escala cinza
            rgba = bytes(b for idx in indices for b in (idx, idx, idx, 255))

        self._pixels_cache = rgba
        return rgba, self.width, self.height


def read_sff_v2(
    path: str,
) -> tuple[list[SpriteInfoV2], list[PaletteInfoV2]]:
    """Lê um arquivo SFF v2 e retorna (sprites, paletas)."""
    with open(path, "rb") as f:
        data = f.read()

    if len(data) < 80:
        raise ValueError("Arquivo SFF v2 inválido (muito curto)")

    # Header
    # Sig já verificada pelo dispatcher
    verhi = data[15]
    if verhi != 2:
        raise ValueError(f"Versão SFF inválida: {verhi} (esperado 2)")

    # Header v2 — offsets relevantes
    ldata_offset = struct.unpack_from("<I", data, 36)[0]
    ldata_length = struct.unpack_from("<I", data, 40)[0]
    tdata_offset = struct.unpack_from("<I", data, 44)[0]
    tdata_length = struct.unpack_from("<I", data, 48)[0]
    nsprites = struct.unpack_from("<I", data, 56)[0]
    images_offset = struct.unpack_from("<I", data, 60)[0]
    npalettes = struct.unpack_from("<I", data, 64)[0]
    palettes_offset = struct.unpack_from("<I", data, 68)[0]

    # --- Lê paletas ---
    palettes: list[PaletteInfoV2] = []
    pal_node_size = 16
    for i in range(npalettes):
        pos = palettes_offset + i * pal_node_size
        if pos + pal_node_size > len(data):
            break
        pal_group = struct.unpack_from("<H", data, pos)[0]
        pal_item = struct.unpack_from("<H", data, pos + 2)[0]
        num_colors = struct.unpack_from("<I", data, pos + 4)[0]
        linked_index = struct.unpack_from("<I", data, pos + 8)[0]
        pal_data_offset = struct.unpack_from("<I", data, pos + 12)[0]

        abs_pal_offset = ldata_offset + pal_data_offset
        colors = _read_palette(data, abs_pal_offset, num_colors)

        palettes.append(PaletteInfoV2(
            group=pal_group,
            item=pal_item,
            num_colors=num_colors,
            linked_index=linked_index,
            data_offset=abs_pal_offset,
            colors=colors,
        ))

    # Resolve links de paleta
    for i, pal in enumerate(palettes):
        if pal.linked_index != 0 and not pal.colors:
            src = pal.linked_index
            if 0 <= src < len(palettes):
                pal.colors = palettes[src].colors

    # --- Lê sprites ---
    sprites: list[SpriteInfoV2] = []
    node_size = 28
    for i in range(nsprites):
        pos = images_offset + i * node_size
        if pos + node_size > len(data):
            break

        grp = struct.unpack_from("<H", data, pos)[0]
        img = struct.unpack_from("<H", data, pos + 2)[0]
        w = struct.unpack_from("<H", data, pos + 4)[0]
        h = struct.unpack_from("<H", data, pos + 6)[0]
        x = struct.unpack_from("<h", data, pos + 8)[0]
        y = struct.unpack_from("<h", data, pos + 10)[0]
        linked_index = struct.unpack_from("<H", data, pos + 12)[0]
        flags = data[pos + 14]
        fmt = data[pos + 15]
        color_depth = struct.unpack_from("<I", data, pos + 16)[0]
        spr_data_offset = struct.unpack_from("<I", data, pos + 20)[0]
        spr_data_length = struct.unpack_from("<I", data, pos + 24)[0]

        # bit 0 do flags: usar tdata (thumbnail) em vez de ldata
        use_tdata = bool(flags & 1)
        if use_tdata:
            abs_offset = tdata_offset + spr_data_offset
        else:
            abs_offset = ldata_offset + spr_data_offset

        sprites.append(SpriteInfoV2(
            group=grp,
            item=img,
            width=w,
            height=h,
            x=x,
            y=y,
            linked_index=linked_index,
            flags=flags,
            fmt=fmt,
            palette_index=color_depth,
            data_offset=abs_offset,
            data_length=spr_data_length,
            use_tdata=use_tdata,
        ))

    # Preenche _data_cache de sprites linkados
    _resolve_linked_sprites(sprites, data)

    return sprites, palettes


def get_sprite_data(spr: SpriteInfoV2, file_data: bytes) -> bytes:
    """Extrai os dados brutos de um sprite do arquivo."""
    start = spr.data_offset
    end = start + spr.data_length
    if end > len(file_data):
        return b""
    return file_data[start:end]


def _resolve_linked_sprites(
    sprites: list[SpriteInfoV2], file_data: bytes
) -> None:
    """Resolve sprites com linkedindex, copiando offset e tamanho."""
    for i, spr in enumerate(sprites):
        if spr.is_linked:
            src_idx = spr.linked_index
            if 0 <= src_idx < len(sprites) and src_idx != i:
                src = sprites[src_idx]
                spr.data_offset = src.data_offset
                spr.data_length = src.data_length
                spr.fmt = src.fmt
                spr.width = src.width
                spr.height = src.height


def _read_palette(
    data: bytes,
    offset: int,
    num_colors: int,
) -> list[tuple[int, int, int, int]]:
    """Lê `num_colors` cores BGRA do offset dado (formato do SFF v2)."""
    colors = []
    for i in range(min(num_colors, 256)):
        pos = offset + i * 4
        if pos + 4 > len(data):
            break
        b, g, r, a = data[pos], data[pos + 1], data[pos + 2], data[pos + 3]
        colors.append((r, g, b, a))
    return colors


def _indices_to_rgba(
    indices: bytes,
    palette: list[tuple[int, int, int, int]],
) -> bytes:
    """Converte índices de paleta em bytes RGBA."""
    out = bytearray(len(indices) * 4)
    for i, idx in enumerate(indices):
        if idx < len(palette):
            r, g, b, a = palette[idx]
        else:
            r, g, b, a = 0, 0, 0, 0
        base = i * 4
        out[base] = r
        out[base + 1] = g
        out[base + 2] = b
        out[base + 3] = a
    return bytes(out)


def _blank_rgba(width: int, height: int) -> bytes:
    return bytes(width * height * 4)
