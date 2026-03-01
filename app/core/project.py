"""
Detecção e validação da pasta raiz de um projeto Ikemen GO / MUGEN.

Estrutura detectada:
  <raiz>/system.def           (ou <raiz>/data/system.def)
  <raiz>/select.def           (ou <raiz>/data/select.def)
  <raiz>/chars/               (ou <raiz>/data/chars/)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from app.utils.path_resolver import PathResolver


class ProjectError(Exception):
    """Erro ao abrir/validar projeto."""


@dataclass
class IkemenProject:
    """Representa um projeto Ikemen GO aberto."""

    root: str                       # Caminho absoluto da raiz
    system_def: str = ""            # Caminho absoluto do system.def
    select_def: str = ""            # Caminho absoluto do select.def
    chars_dir: str = ""             # Caminho absoluto da pasta chars/
    data_dir: str = ""              # Caminho absoluto de data/ (se existir)
    resolver: PathResolver = field(init=False)

    def __post_init__(self) -> None:
        self.resolver = PathResolver(self.root)

    # ------------------------------------------------------------------
    # Criação / abertura
    # ------------------------------------------------------------------

    @classmethod
    def open(cls, path: str) -> "IkemenProject":
        """Abre um projeto a partir de um caminho (raiz ou qualquer arquivo dentro dele).

        Sobe diretórios até encontrar system.def.
        """
        root = cls._find_root(path)
        proj = cls(root=root)
        proj._locate_files()
        return proj

    @staticmethod
    def _find_root(start: str) -> str:
        """Tenta localizar a raiz do projeto subindo na hierarquia."""
        candidate = os.path.normpath(start)
        if not os.path.isdir(candidate):
            candidate = os.path.dirname(candidate)

        # Sobe até 5 níveis procurando system.def
        for _ in range(6):
            if _has_system_def(candidate):
                return candidate
            parent = os.path.dirname(candidate)
            if parent == candidate:
                break
            candidate = parent

        # Tenta o caminho original mesmo assim
        orig = os.path.normpath(start)
        if os.path.isdir(orig):
            return orig
        return os.path.dirname(orig)

    def _locate_files(self) -> None:
        """Localiza system.def, select.def e chars/ dentro da raiz."""
        root = self.root

        # Candidatos de data_dir
        data_candidates = [root, os.path.join(root, "data")]

        found_data = None
        found_system = None
        for base in data_candidates:
            candidate = os.path.join(base, "system.def")
            if os.path.isfile(candidate):
                found_data = base
                found_system = candidate
                break

        if found_system is None:
            raise ProjectError(
                f"system.def não encontrado em '{root}' nem em '{root}/data'."
            )

        self.system_def = found_system
        self.data_dir = found_data or root

        # select.def
        select_candidate = os.path.join(self.data_dir, "select.def")
        if os.path.isfile(select_candidate):
            self.select_def = select_candidate

        # chars/
        chars_candidates = [
            os.path.join(root, "chars"),
            os.path.join(self.data_dir, "chars"),
        ]
        for c in chars_candidates:
            if os.path.isdir(c):
                self.chars_dir = c
                break

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def is_valid(self) -> bool:
        return bool(self.system_def and os.path.isfile(self.system_def))

    def list_characters(self) -> list[str]:
        """Retorna lista de nomes de personagens disponíveis na pasta chars/."""
        if not self.chars_dir or not os.path.isdir(self.chars_dir):
            return []
        chars = []
        for entry in os.scandir(self.chars_dir):
            if entry.is_dir():
                def_file = os.path.join(entry.path, f"{entry.name}.def")
                if os.path.isfile(def_file):
                    chars.append(entry.name)
        return sorted(chars)

    def list_stages(self) -> list[str]:
        """Retorna lista de arquivos .def em stages/."""
        stages_dir = os.path.join(self.root, "stages")
        if not os.path.isdir(stages_dir):
            stages_dir = os.path.join(self.data_dir, "stages")
        if not os.path.isdir(stages_dir):
            return []
        return sorted(
            f"stages/{f}"
            for f in os.listdir(stages_dir)
            if f.lower().endswith(".def")
        )

    def resolve(self, relative: str) -> str:
        return self.resolver.resolve(relative)

    @property
    def name(self) -> str:
        return os.path.basename(self.root)


def _has_system_def(directory: str) -> bool:
    return (
        os.path.isfile(os.path.join(directory, "system.def"))
        or os.path.isfile(os.path.join(directory, "data", "system.def"))
    )
