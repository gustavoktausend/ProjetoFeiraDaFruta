"""
Resolução de paths relativos dentro de um projeto Ikemen GO / MUGEN.
"""

from __future__ import annotations

import os


class PathResolver:
    """Resolve caminhos relativos a partir da raiz do projeto."""

    def __init__(self, project_root: str) -> None:
        self.project_root = os.path.normpath(project_root)

    def resolve(self, relative_path: str) -> str:
        """Converte um path relativo (do projeto) em path absoluto."""
        rel = relative_path.replace("\\", "/").strip()
        if os.path.isabs(rel):
            return os.path.normpath(rel)
        return os.path.normpath(os.path.join(self.project_root, rel))

    def to_relative(self, absolute_path: str) -> str:
        """Converte um path absoluto em relativo à raiz do projeto."""
        try:
            rel = os.path.relpath(absolute_path, self.project_root)
        except ValueError:
            return absolute_path
        return rel.replace("\\", "/")

    def exists(self, relative_path: str) -> bool:
        return os.path.exists(self.resolve(relative_path))

    def join(self, *parts: str) -> str:
        return os.path.normpath(os.path.join(self.project_root, *parts))
