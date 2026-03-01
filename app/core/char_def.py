"""
Mapeamento dos campos conhecidos do arquivo .def de personagem do Ikemen GO / MUGEN.

Reutiliza ParamDef, SectionDef e ParamType de system_def.py sem redefinir.
"""

from __future__ import annotations

from app.core.system_def import ParamDef, ParamType, SectionDef


KNOWN_SECTIONS: list[SectionDef] = [
    SectionDef(
        name="Info",
        label="Informações do Personagem",
        description="Identificação e metadados do personagem.",
        params=[
            ParamDef(
                "name", "Nome", ParamType.STRING,
                description="Nome interno usado em scripts e referências de outros personagens",
            ),
            ParamDef(
                "displayname", "Nome de Exibição", ParamType.STRING,
                description="Nome exibido na tela de seleção e nas telas de vitória",
            ),
            ParamDef(
                "author", "Autor", ParamType.STRING,
                description="Autor ou equipe responsável pelo personagem",
            ),
            ParamDef(
                "versiondate", "Data de Versão", ParamType.STRING,
                description="Data da versão no formato MM,DD,AAAA (ex: 01,01,2024)",
            ),
            ParamDef(
                "mugenversion", "Versão MUGEN", ParamType.ENUM,
                default="1.1",
                description="Versão mínima do engine necessária",
                choices=["1.0", "1.1", "Ikemen"],
            ),
            ParamDef(
                "localcoord", "Coordenadas Locais", ParamType.STRING,
                description="Espaço de coordenadas local (ex: 320,240 para SD, 1280,720 para HD)",
            ),
            ParamDef(
                "p1name", "Nome P1", ParamType.STRING,
                description="Nome alternativo para o perfil do Jogador 1",
            ),
            ParamDef(
                "p2name", "Nome P2", ParamType.STRING,
                description="Nome alternativo para o perfil do Jogador 2",
            ),
            ParamDef(
                "p3name", "Nome P3", ParamType.STRING,
                description="Nome alternativo para o perfil do Jogador 3",
            ),
            ParamDef(
                "p4name", "Nome P4", ParamType.STRING,
                description="Nome alternativo para o perfil do Jogador 4",
            ),
        ],
    ),
    SectionDef(
        name="Files",
        label="Arquivos",
        description="Referências aos arquivos de recursos do personagem.",
        params=[
            ParamDef(
                "cmd", "Comandos (CMD)", ParamType.FILE,
                description="Arquivo de comandos (.cmd) — define inputs e move list",
            ),
            ParamDef(
                "cns", "Estados (CNS)", ParamType.FILE,
                description="Arquivo de estados (.cns) — define comportamentos e animações",
            ),
            ParamDef(
                "stcommon", "Estados Comuns", ParamType.FILE,
                description="Arquivo de estados comuns compartilhados (ex: common1.cns)",
            ),
            ParamDef(
                "sprite", "Sprites (SFF)", ParamType.FILE,
                description="Arquivo de sprites (.sff)",
            ),
            ParamDef(
                "anim", "Animações (AIR)", ParamType.FILE,
                description="Arquivo de animações (.air)",
            ),
            ParamDef(
                "sound", "Sons (SND)", ParamType.FILE,
                description="Arquivo de sons (.snd)",
            ),
            ParamDef("pal1",  "Paleta 1",  ParamType.FILE, description="Paleta alternativa 1 (.act)"),
            ParamDef("pal2",  "Paleta 2",  ParamType.FILE, description="Paleta alternativa 2 (.act)"),
            ParamDef("pal3",  "Paleta 3",  ParamType.FILE, description="Paleta alternativa 3 (.act)"),
            ParamDef("pal4",  "Paleta 4",  ParamType.FILE, description="Paleta alternativa 4 (.act)"),
            ParamDef("pal5",  "Paleta 5",  ParamType.FILE, description="Paleta alternativa 5 (.act)"),
            ParamDef("pal6",  "Paleta 6",  ParamType.FILE, description="Paleta alternativa 6 (.act)"),
            ParamDef("pal7",  "Paleta 7",  ParamType.FILE, description="Paleta alternativa 7 (.act)"),
            ParamDef("pal8",  "Paleta 8",  ParamType.FILE, description="Paleta alternativa 8 (.act)"),
            ParamDef("pal9",  "Paleta 9",  ParamType.FILE, description="Paleta alternativa 9 (.act)"),
            ParamDef("pal10", "Paleta 10", ParamType.FILE, description="Paleta alternativa 10 (.act)"),
            ParamDef("pal11", "Paleta 11", ParamType.FILE, description="Paleta alternativa 11 (.act)"),
            ParamDef("pal12", "Paleta 12", ParamType.FILE, description="Paleta alternativa 12 (.act)"),
            ParamDef(
                "intro.storyboard", "Storyboard Intro", ParamType.FILE,
                description="Storyboard de intro do modo arcade",
            ),
            ParamDef(
                "ending.storyboard", "Storyboard Ending", ParamType.FILE,
                description="Storyboard de ending do modo arcade",
            ),
        ],
    ),
    SectionDef(
        name="Arcade",
        label="Modo Arcade",
        description="Configurações do modo arcade.",
        params=[
            ParamDef(
                "intro.storyboard", "Storyboard Intro", ParamType.FILE,
                description="Storyboard de intro (modo arcade)",
            ),
            ParamDef(
                "ending.storyboard", "Storyboard Ending", ParamType.FILE,
                description="Storyboard de ending (modo arcade)",
            ),
            ParamDef(
                "ai.level", "Nível de IA", ParamType.INT,
                default=4,
                description="Nível padrão de IA (1=fácil … 8=difícil)",
            ),
        ],
    ),
    SectionDef(
        name="Palette Defaults",
        label="Paletas Padrão",
        description="Arquivos de paleta padrão do personagem.",
        params=[
            ParamDef("pal1",  "Paleta Padrão 1",  ParamType.FILE, description="Arquivo de paleta padrão 1 (.act)"),
            ParamDef("pal2",  "Paleta Padrão 2",  ParamType.FILE, description="Arquivo de paleta padrão 2 (.act)"),
            ParamDef("pal3",  "Paleta Padrão 3",  ParamType.FILE, description="Arquivo de paleta padrão 3 (.act)"),
            ParamDef("pal4",  "Paleta Padrão 4",  ParamType.FILE, description="Arquivo de paleta padrão 4 (.act)"),
            ParamDef("pal5",  "Paleta Padrão 5",  ParamType.FILE, description="Arquivo de paleta padrão 5 (.act)"),
            ParamDef("pal6",  "Paleta Padrão 6",  ParamType.FILE, description="Arquivo de paleta padrão 6 (.act)"),
            ParamDef("pal7",  "Paleta Padrão 7",  ParamType.FILE, description="Arquivo de paleta padrão 7 (.act)"),
            ParamDef("pal8",  "Paleta Padrão 8",  ParamType.FILE, description="Arquivo de paleta padrão 8 (.act)"),
            ParamDef("pal9",  "Paleta Padrão 9",  ParamType.FILE, description="Arquivo de paleta padrão 9 (.act)"),
            ParamDef("pal10", "Paleta Padrão 10", ParamType.FILE, description="Arquivo de paleta padrão 10 (.act)"),
            ParamDef("pal11", "Paleta Padrão 11", ParamType.FILE, description="Arquivo de paleta padrão 11 (.act)"),
            ParamDef("pal12", "Paleta Padrão 12", ParamType.FILE, description="Arquivo de paleta padrão 12 (.act)"),
        ],
    ),
]

# Dicionário para lookup rápido por nome de seção
KNOWN_SECTIONS_MAP: dict[str, SectionDef] = {
    s.name.lower(): s for s in KNOWN_SECTIONS
}
