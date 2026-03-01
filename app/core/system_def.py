"""
Modelo de dados para system.def do Ikemen GO / MUGEN.

Mapeia as seções e parâmetros conhecidos com tipo e descrição,
permitindo que o editor gráfico gere os widgets corretos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class ParamType(Enum):
    STRING = auto()       # Texto livre
    INT = auto()          # Número inteiro
    FLOAT = auto()        # Número decimal
    BOOL = auto()         # 0 ou 1
    COLOR = auto()        # R,G,B  (ex: "255, 128, 0")
    FILE = auto()         # Caminho de arquivo
    ENUM = auto()         # Valor de um conjunto fixo


@dataclass
class ParamDef:
    """Definição de um parâmetro dentro de uma seção."""
    key: str
    label: str
    ptype: ParamType
    default: Any = ""
    description: str = ""
    choices: list[str] = field(default_factory=list)  # para ENUM


@dataclass
class SectionDef:
    """Definição de uma seção do system.def."""
    name: str
    label: str
    description: str = ""
    params: list[ParamDef] = field(default_factory=list)


# ------------------------------------------------------------------
# Mapeamento das seções conhecidas do system.def
# ------------------------------------------------------------------

KNOWN_SECTIONS: list[SectionDef] = [
    SectionDef(
        name="Info",
        label="Informações Gerais",
        description="Nome e versão do sistema MUGEN.",
        params=[
            ParamDef("name", "Nome", ParamType.STRING, description="Nome do sistema"),
            ParamDef("author", "Autor", ParamType.STRING, description="Autor do sistema"),
            ParamDef("versiondate", "Data de versão", ParamType.STRING),
            ParamDef("mugenversion", "Versão MUGEN", ParamType.STRING),
        ],
    ),
    SectionDef(
        name="Files",
        label="Arquivos",
        description="Referências a sprites, sons e fontes do sistema.",
        params=[
            ParamDef("spr", "Sprite (SFF)", ParamType.FILE, description="Arquivo de sprites do sistema"),
            ParamDef("snd", "Som (SND)", ParamType.FILE, description="Arquivo de sons do sistema"),
            ParamDef("logo.storyboard", "Storyboard Logo", ParamType.FILE),
            ParamDef("intro.storyboard", "Storyboard Intro", ParamType.FILE),
            ParamDef("select", "Tela de Seleção (DEF)", ParamType.FILE),
            ParamDef("fight", "Tela de Luta (DEF)", ParamType.FILE),
            ParamDef("font1", "Fonte 1", ParamType.FILE),
            ParamDef("font2", "Fonte 2", ParamType.FILE),
            ParamDef("font3", "Fonte 3", ParamType.FILE),
        ],
    ),
    SectionDef(
        name="Music",
        label="Música",
        description="Músicas das telas do sistema.",
        params=[
            ParamDef("title.bgm", "BGM Título", ParamType.FILE),
            ParamDef("select.bgm", "BGM Seleção", ParamType.FILE),
            ParamDef("vs.bgm", "BGM VS Screen", ParamType.FILE),
            ParamDef("victory.bgm", "BGM Vitória", ParamType.FILE),
            ParamDef("title.bgm.loop", "Loop Título", ParamType.BOOL, default="1"),
            ParamDef("select.bgm.loop", "Loop Seleção", ParamType.BOOL, default="1"),
        ],
    ),
    SectionDef(
        name="Title Info",
        label="Tela de Título",
        description="Configurações da tela de título.",
        params=[
            ParamDef("fadein.time", "Tempo Fade In", ParamType.INT, default="30"),
            ParamDef("fadeout.time", "Tempo Fade Out", ParamType.INT, default="30"),
            ParamDef("menu.pos", "Posição do Menu", ParamType.STRING),
            ParamDef("menu.item.font", "Fonte dos Itens", ParamType.STRING),
            ParamDef("menu.item.spacing", "Espaçamento Itens", ParamType.STRING),
        ],
    ),
    SectionDef(
        name="Select Info",
        label="Tela de Seleção",
        description="Configurações da tela de seleção de personagem.",
        params=[
            ParamDef("fadein.time", "Tempo Fade In", ParamType.INT, default="30"),
            ParamDef("fadeout.time", "Tempo Fade Out", ParamType.INT, default="30"),
            ParamDef("rows", "Linhas do Grid", ParamType.INT, default="4"),
            ParamDef("columns", "Colunas do Grid", ParamType.INT, default="5"),
            ParamDef("wrapping", "Wrapping", ParamType.BOOL, default="1"),
            ParamDef("pos", "Posição do Grid", ParamType.STRING),
            ParamDef("showemptyboxes", "Mostrar Caixas Vazias", ParamType.BOOL, default="1"),
            ParamDef("moveoveremptyboxes", "Mover sobre Vazios", ParamType.BOOL, default="1"),
            ParamDef("cell.size", "Tamanho da Célula", ParamType.STRING),
            ParamDef("cell.spacing", "Espaçamento de Célula", ParamType.INT, default="2"),
            ParamDef("cell.bg.spr", "Sprite de Fundo da Célula", ParamType.STRING),
            ParamDef("cell.random.spr", "Sprite Aleatório", ParamType.STRING),
            ParamDef("p1.cursor.startcell", "Célula Inicial P1", ParamType.STRING),
            ParamDef("p2.cursor.startcell", "Célula Inicial P2", ParamType.STRING),
        ],
    ),
    SectionDef(
        name="VS Screen",
        label="Tela VS",
        description="Configurações da tela de confronto.",
        params=[
            ParamDef("time", "Duração (frames)", ParamType.INT, default="150"),
            ParamDef("fadein.time", "Tempo Fade In", ParamType.INT, default="20"),
            ParamDef("fadeout.time", "Tempo Fade Out", ParamType.INT, default="20"),
            ParamDef("p1.pos", "Posição P1", ParamType.STRING),
            ParamDef("p2.pos", "Posição P2", ParamType.STRING),
        ],
    ),
    SectionDef(
        name="Demo Mode",
        label="Modo Demo",
        description="Configurações do modo de demonstração.",
        params=[
            ParamDef("enabled", "Ativado", ParamType.BOOL, default="1"),
            ParamDef("title.waittime", "Espera antes do Demo", ParamType.INT, default="600"),
            ParamDef("fight.endtime", "Duração da Luta Demo", ParamType.INT, default="1500"),
        ],
    ),
    SectionDef(
        name="Game Over Screen",
        label="Tela Game Over",
        params=[
            ParamDef("enabled", "Ativado", ParamType.BOOL, default="1"),
            ParamDef("fadein.time", "Tempo Fade In", ParamType.INT, default="30"),
            ParamDef("fadeout.time", "Tempo Fade Out", ParamType.INT, default="30"),
        ],
    ),
    SectionDef(
        name="Continue Screen",
        label="Tela de Continue",
        params=[
            ParamDef("enabled", "Ativado", ParamType.BOOL, default="1"),
            ParamDef("pos", "Posição", ParamType.STRING),
        ],
    ),
    SectionDef(
        name="Win Screen",
        label="Tela de Vitória",
        params=[
            ParamDef("enabled", "Ativado", ParamType.BOOL, default="1"),
            ParamDef("fadein.time", "Tempo Fade In", ParamType.INT, default="30"),
            ParamDef("fadeout.time", "Tempo Fade Out", ParamType.INT, default="30"),
            ParamDef("showtime", "Tempo de Exibição", ParamType.INT, default="200"),
            ParamDef("pos", "Posição", ParamType.STRING),
        ],
    ),
    SectionDef(
        name="Default Headers",
        label="Cabeçalhos Padrão",
        params=[
            ParamDef("p1.life", "HP P1", ParamType.INT, default="1000"),
            ParamDef("p2.life", "HP P2", ParamType.INT, default="1000"),
            ParamDef("time", "Tempo de Luta", ParamType.INT, default="99"),
            ParamDef("p1.power", "Power P1", ParamType.INT, default="3000"),
            ParamDef("p2.power", "Power P2", ParamType.INT, default="3000"),
        ],
    ),
]

# Dicionário para lookup rápido por nome
KNOWN_SECTIONS_MAP: dict[str, SectionDef] = {
    s.name.lower(): s for s in KNOWN_SECTIONS
}
