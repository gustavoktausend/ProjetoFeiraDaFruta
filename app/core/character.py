"""
Modelo de dados para um personagem do Ikemen GO / MUGEN.

Estrutura de arquivo de personagem:
  chars/<nome>/
    <nome>.def     — Definição principal (referencia .cns, .cmd, .sff, etc.)
    <nome>.cns     — States (estado machine, constantes, variáveis)
    <nome>.cmd     — Comandos (inputs) e state controllers
    <nome>.sff     — Sprites
    <nome>.snd     — Sons
    <nome>.air     — Animações
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from app.core import ini_parser


@dataclass
class CharacterFiles:
    """Caminhos dos arquivos de um personagem."""
    def_path: str
    cns_paths: list[str] = field(default_factory=list)
    cmd_paths: list[str] = field(default_factory=list)
    sff_path: str = ""
    snd_path: str = ""
    air_path: str = ""
    name: str = ""
    display_name: str = ""
    author: str = ""


def load_character(def_path: str) -> CharacterFiles:
    """Carrega um personagem a partir do arquivo .def.

    Lê o .def e resolve os paths dos outros arquivos.
    """
    char_dir = os.path.dirname(def_path)

    doc = ini_parser.load(def_path)

    # Seção [Info]
    name = doc.get("Info", "name")
    display_name = doc.get("Info", "displayname") or name
    author = doc.get("Info", "author")

    cf = CharacterFiles(
        def_path=def_path,
        name=name,
        display_name=display_name,
        author=author,
    )

    # Seção [Files]
    def _resolve(relative: str) -> str:
        if not relative:
            return ""
        p = os.path.join(char_dir, relative.replace("\\", "/"))
        return os.path.normpath(p) if os.path.exists(os.path.normpath(p)) else ""

    files_section = doc.section("Files")
    if files_section:
        for entry in files_section.entries:
            key = entry.key.lower()
            val = entry.value.strip()
            if not key or not val:
                continue
            if key in ("cns", "stcommon") or key.startswith("cns"):
                resolved = _resolve(val)
                if resolved:
                    cf.cns_paths.append(resolved)
            elif key == "cmd":
                resolved = _resolve(val)
                if resolved:
                    cf.cmd_paths.append(resolved)
            elif key == "sprite":
                cf.sff_path = _resolve(val)
            elif key == "sound":
                cf.snd_path = _resolve(val)
            elif key == "anim":
                cf.air_path = _resolve(val)

    # Heurística: se não achou, procura arquivos padrão
    basename = os.path.splitext(os.path.basename(def_path))[0]
    if not cf.cns_paths:
        default_cns = os.path.join(char_dir, f"{basename}.cns")
        if os.path.isfile(default_cns):
            cf.cns_paths.append(default_cns)
    if not cf.cmd_paths:
        default_cmd = os.path.join(char_dir, f"{basename}.cmd")
        if os.path.isfile(default_cmd):
            cf.cmd_paths.append(default_cmd)
    if not cf.sff_path:
        default_sff = os.path.join(char_dir, f"{basename}.sff")
        if os.path.isfile(default_sff):
            cf.sff_path = default_sff

    return cf
