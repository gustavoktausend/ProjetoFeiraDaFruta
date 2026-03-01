# MugemUI — Editor Gráfico para Projetos Ikemen GO

Editor visual em **Python + PySide6** para configurar projetos **Ikemen GO** (engine de jogos de luta, fork open-source do MUGEN) sem precisar editar arquivos de texto manualmente.

---

## Funcionalidades

### Editor Visual de system.def
Formulário organizado por seções com widgets apropriados para cada tipo de parâmetro (texto, inteiro, booleano, cor, arquivo, enum). Preserva comentários e formatação original ao salvar.

### Editor de Roster (select.def)
Interface drag-and-drop para reorganizar a ordem dos personagens na tela de seleção. Suporta o formato CSV especial do select.def com campos `chave=valor` por linha.

### Editor Visual de .def de Personagem
Formulário completo para edição do arquivo `.def` de personagem, com:
- Seções **[Info]**, **[Files]**, **[Arcade]** e **[Palette Defaults]** mapeadas com descrições de cada campo
- Indicadores **✓/✗** de existência de arquivo para todos os campos do tipo FILE
- Widget especializado para `versiondate` (spinboxes MM/DD/AAAA)
- Widget especializado para `localcoord` com dica contextual (SD 320×240 / HD 1280×720)
- **Preview do portrait** do personagem (sprites 9000,0 e 9000,1) carregado em background thread
- Painel de status listando todos os arquivos referenciados e quantos foram encontrados

### Editor de Texto (.CNS / .CMD / .AIR)
Editor com **syntax highlighting** para arquivos de estados e comandos do MUGEN, com suporte a seções duplicadas (`[Command]`, `[StateDef]`, `[State]`).

### Visualizador de Sprites (SFF)
Visualizador com zoom/pan para arquivos SFF v1 e v2, com árvore de grupos/itens e carregamento em background thread.

---

## Stack

| Tecnologia | Versão | Uso |
|---|---|---|
| Python | 3.14+ | Linguagem principal |
| PySide6 | 6.6+ | Interface gráfica (Qt6) |
| Pillow | 10+ | Decodificação PCX (SFF v1) e PNG embutido (SFF v2) |
| chardet | 5+ | Detecção de encoding (latin-1 vs UTF-8) |
| pytest | — | Testes unitários |

---

## Instalação e Uso

```bash
# Clonar o repositório
git clone https://github.com/gustavoktausend/ProjetoFeiraDaFruta.git
cd ProjetoFeiraDaFruta

# Instalar dependências
pip install -r requirements.txt

# Executar o editor
python main.py
```

Ao abrir, clique em **"Abrir Projeto…"** e selecione a pasta raiz de um projeto Ikemen GO. O editor detecta automaticamente o `system.def` subindo até 5 níveis de diretório.

---

## Estrutura do Projeto

```
projetoMugemUI/
├── main.py                        # Ponto de entrada
├── requirements.txt
├── app/
│   ├── core/                      # Lógica de negócio (sem UI)
│   │   ├── ini_parser.py          # Parser/writer round-trip do formato INI-like MUGEN
│   │   ├── project.py             # Detecção e validação da pasta raiz do Ikemen GO
│   │   ├── system_def.py          # Mapeamento das seções/parâmetros do system.def
│   │   ├── char_def.py            # Mapeamento das seções/parâmetros do .def de personagem
│   │   ├── select_def.py          # Parser do select.def (formato CSV especial)
│   │   ├── character.py           # Carregamento de personagem a partir do .def
│   │   └── sff/
│   │       ├── sff_reader.py      # Dispatcher v1/v2 por verhi byte (offset 15)
│   │       ├── sff_v1.py          # Leitor SFF v1 (lista ligada + PCX)
│   │       ├── sff_v1_pcx.py      # Decodificação PCX via Pillow + fallback manual
│   │       ├── sff_v2.py          # Leitor SFF v2 (sprite nodes de 28 bytes)
│   │       └── decompressor.py    # Raw, RLE8, RLE5, LZ5, PNG embutido
│   ├── ui/
│   │   ├── main_window.py         # QMainWindow + QTabWidget + dirty tracking
│   │   └── widgets/
│   │       ├── welcome_panel.py        # Tela inicial
│   │       ├── system_def_editor.py    # Formulário visual do system.def
│   │       ├── roster_editor.py        # Editor drag-and-drop do select.def
│   │       ├── character_editor.py     # Editor com aba "Visual DEF" + editor de texto
│   │       ├── def_editor.py           # Editor visual do .def com preview de portrait
│   │       └── sprite_viewer.py        # QGraphicsView com zoom/pan + thread de carregamento
│   └── utils/
│       ├── encoding.py            # Detecção UTF-8/latin-1 + read/write helpers
│       └── path_resolver.py       # Resolução de paths relativos à raiz do projeto
└── tests/
    ├── test_ini_parser.py         # Testes do parser INI
    └── test_sff_reader.py         # Testes dos descompressores SFF
```

---

## Testes

```bash
# Todos os testes
python -m pytest tests/ -v

# Arquivo específico
python -m pytest tests/test_ini_parser.py -v
python -m pytest tests/test_sff_reader.py -v
```

---

## Detalhes Técnicos

### Parser INI (ini_parser.py)
O `configparser` padrão do Python não é utilizado pois não suporta seções duplicadas (ex: múltiplos `[Command]` em arquivos `.CMD`) nem preserva comentários inline em round-trip. O parser customizado usa `list[IniSection]` em vez de `dict` e armazena cada comentário em `IniEntry.comment`.

### Versões de SFF
O byte no **offset 15** (`verhi`) define a versão do arquivo de sprites:
- `1` → SFF v1 (MUGEN clássico, sprites PCX em lista ligada)
- `2` → SFF v2 (MUGEN 1.x / Ikemen GO, sprite nodes de 28 bytes)

### Performance
O carregamento de SFF e o preview de portrait usam `QRunnable` + `QThreadPool` para não travar a interface durante operações pesadas.
