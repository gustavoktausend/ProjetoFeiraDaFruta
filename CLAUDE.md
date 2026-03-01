# MugemUI — Editor Gráfico para Projetos Ikemen GO

Editor visual em Python + PySide6 para configurar projetos **Ikemen GO** (engine de jogos de luta, fork open-source do MUGEN) sem editar arquivos de texto manualmente.

---

## Stack

- **Python 3.14+**
- **PySide6 6.6+** — UI (QMainWindow, QTabWidget, QGraphicsView, QAbstractItemModel)
- **Pillow 10+** — Decodificação de PCX (SFF v1) e PNG embutido (SFF v2)
- **chardet 5+** — Detecção de encoding (latin-1 vs UTF-8)
- **pytest** — Testes unitários

---

## Comandos Essenciais

```bash
# Instalar dependências
pip install -r requirements.txt

# Rodar o app
python main.py

# Rodar todos os testes
python -m pytest tests/ -v

# Rodar um arquivo de testes específico
python -m pytest tests/test_ini_parser.py -v
python -m pytest tests/test_sff_reader.py -v
```

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
│   │   ├── widgets/
│   │   │   ├── welcome_panel.py        # Tela inicial
│   │   │   ├── system_def_editor.py    # Formulário visual do system.def
│   │   │   ├── roster_editor.py        # Editor drag-and-drop do select.def
│   │   │   ├── character_editor.py     # Editor .CNS/.CMD com syntax highlighting
│   │   │   └── sprite_viewer.py        # QGraphicsView com zoom/pan + thread de carregamento
│   │   ├── models/
│   │   │   ├── roster_model.py         # QAbstractListModel com drag-drop
│   │   │   └── sprite_group_model.py   # QAbstractItemModel (Grupo → Item)
│   │   └── syntax/
│   │       └── mugen_highlighter.py    # QSyntaxHighlighter para .CNS/.CMD
│   └── utils/
│       ├── encoding.py            # Detecção UTF-8/latin-1 + read/write helpers
│       └── path_resolver.py       # Resolução de paths relativos à raiz do projeto
└── tests/
    ├── test_ini_parser.py         # Testes do parser INI (seções duplicadas, round-trip, etc.)
    └── test_sff_reader.py         # Testes dos descompressores (RLE8, RLE5, LZ5, raw)
```

---

## Arquitetura — Decisões Importantes

### ini_parser.py (crítico)
O `configparser` padrão do Python **não pode ser usado**. Problemas que ele não resolve:
- **Seções duplicadas** — arquivos `.CMD` têm múltiplos `[Command]`; o parser usa `list[IniSection]`, não `dict`
- **Round-trip fiel** — comentários inline após `;` são armazenados em `IniEntry.comment` e reescritos na mesma posição
- **Nomes de seção complexos** — `[StateDef 200]`, `[State 200, 0]` são válidos
- **Comentários antes da primeira seção** — vão para `MugenIniDocument.preamble`, não para `header_lines`

### Detecção de versão SFF
O byte no **offset 15** (`verhi`) define a versão:
- `1` → SFF v1 (MUGEN clássico, sprites PCX em lista ligada)
- `2` → SFF v2 (MUGEN 1.x / Ikemen GO, sprite nodes de 28 bytes)

### SFF v2 — offsets críticos
- Campo `offset` do sprite node é **relativo a `ldata_offset`** do header (não ao início do arquivo)
- `linked_index = 0xFFFF` significa **sem link** (não `0`)
- Nós de paleta têm dados BGRA (não RGBA) — converter ao ler
- Bit 0 do `flags`: se set, dados vêm do `tdata` (thumbnail) em vez do `ldata`

### select.def — seção [Characters]
Não é chave=valor. É uma linha CSV onde:
- Campo 0: nome do personagem
- Campo 1: caminho da stage (opcional)
- Demais campos: `chave=valor` (ex: `music=bgm.mp3`, `includestage=1`)

### Performance SFF
Carregamento de SFF usa `QRunnable` + `QThreadPool` para não travar a UI. O `SpriteViewer` emite sinais quando o carregamento termina.

### Detecção da raiz do projeto
`IkemenProject.open(path)` sobe até 5 níveis de diretório procurando `system.def` ou `data/system.def`. Falha com `ProjectError` se não encontrar.

---

## Fluxo Principal

```
Usuário clica "Abrir Projeto"
  → IkemenProject.open(path)         # valida e localiza arquivos
  → MainWindow._open_project_tabs()  # cria tabs lazy

Usuário edita campo
  → widget emite changed()
  → documento marcado como dirty (*no título)

Usuário clica "Salvar Tudo"
  → SystemDefEditor.save() → MugenIniDocument.save()   # preserva comentários
  → RosterEditor.save()    → SelectDefDocument.save()

Usuário seleciona personagem no roster
  → CharacterEditor.load(def_path)
  → SpriteViewer.load_sff(sff_path)   # via QRunnable em background
  → SpriteGroupModel.set_sheet(sheet)

Usuário clica item no TreeView de sprites
  → SpriteSheet.get_rgba(group, item)  # decomprime on-demand
  → QGraphicsView exibe pixmap
```

---

## Adicionando Suporte a Novos Parâmetros do system.def

Edite `app/core/system_def.py` e adicione um `ParamDef` na seção correspondente (ou crie uma nova `SectionDef`). O `SystemDefEditor` gera os widgets automaticamente baseado no `ParamType`.

Tipos disponíveis: `STRING`, `INT`, `FLOAT`, `BOOL`, `COLOR`, `FILE`, `ENUM`.

## Adicionando Suporte a Novo Formato de Compressão SFF

Implemente a função em `app/core/sff/decompressor.py` e adicione o número do método no dispatcher `decompress()`.
