"""
Dispatcher de leitura de SFF: detecta versão e delega ao leitor correto.

Versão detectada pelo byte no offset 15 (verhi):
  1 → SFF v1 (MUGEN clássico, sprites PCX)
  2 → SFF v2 (MUGEN 1.x / Ikemen GO, sprites comprimidos)
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Union

from app.core.sff.sff_v1 import SpriteInfoV1, read_sff_v1
from app.core.sff.sff_v2 import PaletteInfoV2, SpriteInfoV2, get_sprite_data, read_sff_v2


SIGNATURE = b"ElecbyteSpr\x00"


@dataclass
class SpriteSheet:
    """Representa um SFF carregado (v1 ou v2)."""
    version: int    # 1 ou 2
    path: str
    # v1
    sprites_v1: list[SpriteInfoV1] = field(default_factory=list)
    shared_palette_v1: list[tuple[int, int, int]] | None = None
    # v2
    sprites_v2: list[SpriteInfoV2] = field(default_factory=list)
    palettes_v2: list[PaletteInfoV2] = field(default_factory=list)
    # Dados brutos do arquivo (carregados uma vez para v2)
    _file_data: bytes = field(default=b"", repr=False)

    # Cache: (group, item) → QImage ou None
    _image_cache: dict[tuple[int, int], object] = field(
        default_factory=dict, repr=False
    )

    # ------------------------------------------------------------------
    # Acesso unificado
    # ------------------------------------------------------------------

    def groups(self) -> list[int]:
        """Retorna lista ordenada de grupos."""
        if self.version == 1:
            return sorted(set(s.group for s in self.sprites_v1))
        return sorted(set(s.group for s in self.sprites_v2))

    def items_in_group(self, group: int) -> list[int]:
        """Retorna lista ordenada de itens em um grupo."""
        if self.version == 1:
            return sorted(
                s.item for s in self.sprites_v1 if s.group == group
            )
        return sorted(
            s.item for s in self.sprites_v2 if s.group == group
        )

    def sprite_info(self, group: int, item: int) -> SpriteInfoV1 | SpriteInfoV2 | None:
        if self.version == 1:
            for s in self.sprites_v1:
                if s.group == group and s.item == item:
                    return s
        else:
            for s in self.sprites_v2:
                if s.group == group and s.item == item:
                    return s
        return None

    def all_sprites(self) -> list[SpriteInfoV1 | SpriteInfoV2]:
        if self.version == 1:
            return list(self.sprites_v1)
        return list(self.sprites_v2)

    def get_rgba(self, group: int, item: int) -> tuple[bytes, int, int] | None:
        """Obtém pixels RGBA para o sprite (group, item).

        Retorna (bytes_rgba, width, height) ou None se não encontrado.
        """
        spr = self.sprite_info(group, item)
        if spr is None:
            return None

        if self.version == 1:
            assert isinstance(spr, SpriteInfoV1)
            try:
                with open(self.path, "rb") as f:
                    palette = None
                    if spr.same_palette:
                        palette = self.shared_palette_v1
                    rgba, w, h = spr.to_rgba(f, palette)
                    return rgba, w, h
            except Exception:
                return None

        else:
            assert isinstance(spr, SpriteInfoV2)
            raw = get_sprite_data(spr, self._file_data)
            palette = None
            if 0 <= spr.palette_index < len(self.palettes_v2):
                palette = self.palettes_v2[spr.palette_index].colors
            try:
                rgba, w, h = spr.to_rgba(raw, palette)
                return rgba, w, h
            except Exception:
                return None

    def count(self) -> int:
        if self.version == 1:
            return len(self.sprites_v1)
        return len(self.sprites_v2)


# ------------------------------------------------------------------
# Leitura
# ------------------------------------------------------------------

def load(path: str) -> SpriteSheet:
    """Detecta a versão e carrega o SFF."""
    version = detect_version(path)
    if version == 1:
        return _load_v1(path)
    if version == 2:
        return _load_v2(path)
    raise ValueError(f"Versão SFF não suportada: {version}")


def detect_version(path: str) -> int:
    """Lê apenas o byte de versão (offset 15) sem carregar o arquivo todo."""
    with open(path, "rb") as f:
        header = f.read(16)
    if len(header) < 16:
        raise ValueError("Arquivo SFF muito curto")
    if header[:12] != SIGNATURE:
        raise ValueError("Assinatura SFF inválida")
    return header[15]


def _load_v1(path: str) -> SpriteSheet:
    sprites, shared_palette = read_sff_v1(path)
    return SpriteSheet(
        version=1,
        path=path,
        sprites_v1=sprites,
        shared_palette_v1=shared_palette,
    )


def _load_v2(path: str) -> SpriteSheet:
    with open(path, "rb") as f:
        file_data = f.read()
    sprites, palettes = read_sff_v2(path)
    return SpriteSheet(
        version=2,
        path=path,
        sprites_v2=sprites,
        palettes_v2=palettes,
        _file_data=file_data,
    )
