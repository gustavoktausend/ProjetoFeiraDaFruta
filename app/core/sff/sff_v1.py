"""
Leitor do formato SFF v1 do MUGEN.

Estrutura do header (512 bytes):
  Offset  Tamanho  Descrição
  0       12       Assinatura "ElecbyteSpr\0"
  12      1        verlo3
  13      1        verlo2
  14      1        verlo1
  15      1        verhi (deve ser 1)
  16      4        Número de grupos
  20      4        Número de imagens
  24      4        Offset do primeiro subfile (normalmente 512)
  28      4        Subheader size
  32      1        palette_type (0=compartilhada, 1=individual)
  33      479      Reservado

Subheader de cada sprite (32 bytes):
  0       4        Offset do próximo subfile (0 = último)
  4       4        Tamanho dos dados
  8       2        X offset (signed)
  10      2        Y offset (signed)
  12      2        Group number
  14      2        Image number
  16      2        Linked index (0 = não linked)
  18      1        Same palette (1 = usa paleta do sprite anterior)
  19      13       Reservado
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from io import BufferedReader

from app.core.sff.sff_v1_pcx import pcx_to_rgba


@dataclass
class SpriteInfoV1:
    """Informação de um sprite SFF v1."""
    group: int
    item: int
    x: int
    y: int
    linked_index: int
    same_palette: bool
    data_offset: int     # offset do dado PCX no arquivo
    data_size: int
    _data_cache: bytes | None = field(default=None, repr=False)
    _palette_cache: list[tuple[int, int, int]] | None = field(default=None, repr=False)

    def load_data(self, f: BufferedReader) -> bytes:
        if self._data_cache is not None:
            return self._data_cache
        f.seek(self.data_offset)
        self._data_cache = f.read(self.data_size)
        return self._data_cache

    def to_rgba(
        self,
        f: BufferedReader,
        shared_palette: list[tuple[int, int, int]] | None = None,
    ) -> tuple[bytes, int, int]:
        """Retorna (bytes RGBA, width, height)."""
        raw = self.load_data(f)
        palette = shared_palette if self.same_palette else None
        return pcx_to_rgba(raw, palette)


def read_sff_v1(
    path: str,
) -> tuple[list[SpriteInfoV1], list[tuple[int, int, int]] | None]:
    """Lê um arquivo SFF v1 e retorna (sprites, paleta_compartilhada)."""
    sprites: list[SpriteInfoV1] = []
    shared_palette: list[tuple[int, int, int]] | None = None

    with open(path, "rb") as f:
        # Header
        header = f.read(512)
        if len(header) < 32:
            raise ValueError("Arquivo SFF v1 inválido (header muito curto)")

        num_images = struct.unpack_from("<I", header, 20)[0]
        first_offset = struct.unpack_from("<I", header, 24)[0]
        palette_type = header[32]  # 0=compartilhada, 1=individual

        current_offset = first_offset
        for i in range(num_images):
            if current_offset == 0:
                break
            f.seek(current_offset)
            sub = f.read(32)
            if len(sub) < 32:
                break

            next_offset = struct.unpack_from("<I", sub, 0)[0]
            data_size = struct.unpack_from("<I", sub, 4)[0]
            x = struct.unpack_from("<h", sub, 8)[0]
            y = struct.unpack_from("<h", sub, 10)[0]
            group = struct.unpack_from("<H", sub, 12)[0]
            image = struct.unpack_from("<H", sub, 14)[0]
            linked_index = struct.unpack_from("<H", sub, 16)[0]
            same_palette = sub[18] != 0

            data_start = current_offset + 32

            sprite = SpriteInfoV1(
                group=group,
                item=image,
                x=x,
                y=y,
                linked_index=linked_index,
                same_palette=same_palette,
                data_offset=data_start,
                data_size=data_size,
            )
            sprites.append(sprite)

            # Extrai paleta compartilhada do primeiro sprite (se aplicável)
            if i == 0 and palette_type == 0 and data_size > 128:
                f.seek(data_start)
                pcx_data = f.read(data_size)
                shared_palette = _extract_pcx_palette(pcx_data)

            if next_offset == 0:
                break
            current_offset = next_offset

    return sprites, shared_palette


def _extract_pcx_palette(pcx_data: bytes) -> list[tuple[int, int, int]] | None:
    """Extrai a paleta de 256 cores do final do PCX (marcador 0x0C)."""
    if len(pcx_data) < 769:
        return None
    if pcx_data[-769] != 0x0C:
        return None
    palette_data = pcx_data[-768:]
    palette = []
    for i in range(256):
        r = palette_data[i * 3]
        g = palette_data[i * 3 + 1]
        b = palette_data[i * 3 + 2]
        palette.append((r, g, b))
    return palette
