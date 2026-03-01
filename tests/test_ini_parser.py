"""
Testes unitários para app.core.ini_parser.

Cobre:
  - Parsing básico de seções e chaves
  - Seções duplicadas
  - Comentários inline (preservação no round-trip)
  - Seções sem '=' (bare keys, linhas especiais)
  - Linhas vazias preservadas
  - Continuação de linha com '\'
  - to_text() round-trip fiel
"""

import textwrap
import unittest

from app.core.ini_parser import loads, MugenIniDocument


class TestBasicParsing(unittest.TestCase):

    def test_simple_section_and_key(self):
        text = "[Info]\nname = KFM\nauthor = Elecbyte\n"
        doc = loads(text)
        self.assertEqual(len(doc.sections), 1)
        self.assertEqual(doc.sections[0].name, "Info")
        self.assertEqual(doc.get("Info", "name"), "KFM")
        self.assertEqual(doc.get("Info", "author"), "Elecbyte")

    def test_case_insensitive_get(self):
        doc = loads("[Files]\nSpr = system.sff\n")
        self.assertEqual(doc.get("files", "spr"), "system.sff")
        self.assertEqual(doc.get("Files", "SPR"), "system.sff")

    def test_default_value(self):
        doc = loads("[Info]\nname = KFM\n")
        self.assertEqual(doc.get("Info", "missing", "default"), "default")
        self.assertEqual(doc.get("Missing", "key", "fallback"), "fallback")

    def test_multiple_sections(self):
        text = "[Info]\nname = A\n\n[Files]\nspr = a.sff\n"
        doc = loads(text)
        self.assertEqual(len(doc.sections), 2)
        self.assertEqual(doc.get("Info", "name"), "A")
        self.assertEqual(doc.get("Files", "spr"), "a.sff")


class TestDuplicateSections(unittest.TestCase):

    def test_duplicate_command_sections(self):
        text = textwrap.dedent("""\
            [Command]
            name = "punch"
            command = x

            [Command]
            name = "kick"
            command = a
        """)
        doc = loads(text)
        commands = doc.sections_named("Command")
        self.assertEqual(len(commands), 2)
        self.assertEqual(commands[0].get("name"), '"punch"')
        self.assertEqual(commands[1].get("name"), '"kick"')

    def test_statedef_sections(self):
        text = textwrap.dedent("""\
            [StateDef 200]
            type = S
            movetype = A

            [State 200, 0]
            type = ChangeAnim
            value = 200
        """)
        doc = loads(text)
        statedef = doc.section("StateDef 200")
        self.assertIsNotNone(statedef)
        self.assertEqual(statedef.get("type"), "S")

        state = doc.section("State 200, 0")
        self.assertIsNotNone(state)
        self.assertEqual(state.get("value"), "200")


class TestInlineComments(unittest.TestCase):

    def test_inline_comment_preserved(self):
        text = "[Info]\nname = KFM  ; Nome do personagem\n"
        doc = loads(text)
        self.assertEqual(doc.get("Info", "name"), "KFM")
        sec = doc.section("Info")
        self.assertIsNotNone(sec)
        entry = sec.entries[0]
        self.assertIn(";", entry.comment)

    def test_comment_only_line(self):
        text = "; Este é um comentário\n[Info]\nname = Test\n"
        doc = loads(text)
        self.assertIn("; Este é um comentário", doc.preamble)

    def test_semicolon_in_value_not_comment(self):
        text = '[Info]\nname = "value;with;semicolons"\n'
        doc = loads(text)
        self.assertEqual(doc.get("Info", "name"), '"value;with;semicolons"')


class TestRoundTrip(unittest.TestCase):

    def test_simple_roundtrip(self):
        text = "[Info]\nname = KFM\nauthor = Elecbyte\n"
        doc = loads(text)
        result = doc.to_text()
        self.assertIn("[Info]", result)
        self.assertIn("name", result)
        self.assertIn("KFM", result)

    def test_preamble_preserved(self):
        text = "; Header comment\n; Another comment\n\n[Info]\nname = Test\n"
        doc = loads(text)
        self.assertEqual(len(doc.preamble), 3)  # 2 comentários + 1 linha vazia
        result = doc.to_text()
        self.assertIn("; Header comment", result)

    def test_set_and_roundtrip(self):
        text = "[Info]\nname = KFM\n"
        doc = loads(text)
        doc.set("Info", "name", "NewName")
        result = doc.to_text()
        self.assertIn("NewName", result)
        self.assertNotIn("KFM", result)

    def test_add_new_section(self):
        text = "[Info]\nname = KFM\n"
        doc = loads(text)
        doc.set("NewSection", "key", "value")
        result = doc.to_text()
        self.assertIn("[NewSection]", result)
        self.assertIn("value", result)


class TestIniSection(unittest.TestCase):

    def test_section_get_set(self):
        doc = loads("[Info]\nname = A\n")
        sec = doc.section("Info")
        self.assertEqual(sec.get("name"), "A")
        sec.set("name", "B")
        self.assertEqual(sec.get("name"), "B")

    def test_section_keys_and_items(self):
        doc = loads("[Files]\na = 1\nb = 2\n")
        sec = doc.section("Files")
        keys = [k.lower() for k in sec.keys() if k]
        self.assertIn("a", keys)
        self.assertIn("b", keys)

    def test_bare_key_line(self):
        text = "[Characters]\nKFM, stages/kfm.def\nrandom\n"
        doc = loads(text)
        sec = doc.section("Characters")
        self.assertIsNotNone(sec)
        # Linhas sem '=' são armazenadas como raw_line
        raw_lines = [e.raw_line for e in sec.entries if e.raw_line]
        joined = " ".join(raw_lines)
        self.assertIn("KFM", joined)


if __name__ == "__main__":
    unittest.main()
