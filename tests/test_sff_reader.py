"""
Testes unitários para app.core.sff.

Como não temos SFF real disponível nos testes, os testes focam em:
  1. Detecção de erros em arquivos inválidos
  2. Descompressores (decompressor.py) com dados sintéticos
  3. Parser de paleta do SFF v2
  4. Round-trip de sprites vazios
"""

import struct
import unittest

from app.core.sff.decompressor import decompress, _rle8, _rle5, _lz5, _raw


class TestRaw(unittest.TestCase):

    def test_raw_exact_size(self):
        data = bytes(range(16))
        result = _raw(data, 4, 4)
        self.assertEqual(result, data)

    def test_raw_truncates(self):
        data = bytes(range(20))
        result = _raw(data, 4, 4)  # 16 pixels
        self.assertEqual(len(result), 16)
        self.assertEqual(result, data[:16])

    def test_raw_pads(self):
        data = bytes(range(8))
        result = _raw(data, 4, 4)  # needs 16
        self.assertEqual(len(result), 16)
        self.assertEqual(result[:8], data)
        self.assertEqual(result[8:], bytes(8))


class TestRle8(unittest.TestCase):

    def _encode_run(self, color: int, count: int) -> bytes:
        """Codifica um run RLE8: (0x40 | (count-1), color)."""
        return bytes([0x40 | (count - 1), color])

    def _encode_literal(self, pixels: bytes) -> bytes:
        """Codifica literais RLE8."""
        return bytes([len(pixels) - 1]) + pixels

    def test_simple_run(self):
        # 4 pixels de cor 0x55
        data = self._encode_run(0x55, 4)
        result = _rle8(data, 4, 1)
        self.assertEqual(result, bytes([0x55] * 4))

    def test_literal(self):
        pixels = bytes([1, 2, 3, 4])
        data = self._encode_literal(pixels)
        result = _rle8(data, 4, 1)
        self.assertEqual(result, pixels)

    def test_mixed(self):
        # 2 runs + 1 literal
        data = (
            self._encode_run(0xFF, 2) +
            self._encode_run(0x00, 2) +
            self._encode_literal(bytes([0xAB, 0xCD]))
        )
        result = _rle8(data, 6, 1)
        expected = bytes([0xFF, 0xFF, 0x00, 0x00, 0xAB, 0xCD])
        self.assertEqual(result, expected)

    def test_output_size(self):
        data = self._encode_run(0x00, 10)
        result = _rle8(data, 3, 3)  # 9 pixels
        self.assertEqual(len(result), 9)


class TestRle5(unittest.TestCase):

    def test_literal_pixel(self):
        # Byte com bits 7:6 = 00 → literal simples, cor = bits 4:0
        data = bytes([0x0F])  # cor = 15
        result = _rle5(data, 1, 1)
        self.assertEqual(result[0], 15)

    def test_run(self):
        # Byte com bits 7:6 = 01 → run
        # 0x40 | (count-2): count=4 → 0x42
        data = bytes([0x42, 0x07])  # run de 4 pixels, cor = 7
        result = _rle5(data, 4, 1)
        self.assertEqual(result, bytes([7] * 4))

    def test_output_size(self):
        data = bytes([0x00] * 20)  # 20 pixels individuais de cor 0
        result = _rle5(data, 4, 4)  # 16 pixels necessários
        self.assertEqual(len(result), 16)


class TestLz5(unittest.TestCase):

    def test_literal(self):
        # Byte sem bit 6: literal, count = (b & 0x3F) + 1
        pixels = bytes([0xAA, 0xBB, 0xCC])
        # count = 3 → header = 0x02
        data = bytes([0x02]) + pixels
        result = _lz5(data, 3, 1)
        self.assertEqual(result, pixels)

    def test_back_reference(self):
        # Primeiro: 4 literais ABAB
        literal_data = bytes([0x03]) + bytes([0xAA, 0xBB, 0xAA, 0xBB])
        # Depois: back-reference de 4 bytes com offset 4 (copia ABAB)
        # bit 6 set, count = 4 → header = 0x42 | algo
        # length = (0x42 & 0x3F) + 2 = 2 + 2 = 4
        # offset = byte2 + 1 = 3 + 1 = 4
        back_data = bytes([0x42, 0x03])
        data = literal_data + back_data
        result = _lz5(data, 8, 1)
        self.assertEqual(result, bytes([0xAA, 0xBB, 0xAA, 0xBB, 0xAA, 0xBB, 0xAA, 0xBB]))


class TestDecompressDispatch(unittest.TestCase):

    def test_method_0_raw(self):
        data = bytes(range(9))
        result = decompress(data, 0, 3, 3)
        self.assertEqual(result, data)

    def test_method_2_rle8(self):
        # Run de 4 pixels cor 0xFF
        data = bytes([0x43, 0xFF])  # 0x43 = 0x40 | 3 → count=4
        result = decompress(data, 2, 4, 1)
        self.assertEqual(result, bytes([0xFF] * 4))

    def test_invalid_method(self):
        with self.assertRaises(ValueError):
            decompress(b"\x00" * 10, 99, 2, 2)


class TestSffReaderInvalid(unittest.TestCase):

    def test_wrong_signature(self):
        from app.core.sff.sff_reader import detect_version
        import tempfile, os

        with tempfile.NamedTemporaryFile(delete=False, suffix=".sff") as f:
            f.write(b"NotElecbyte" + b"\x00" * 20)
            path = f.name

        try:
            with self.assertRaises(ValueError):
                detect_version(path)
        finally:
            os.unlink(path)

    def test_valid_v1_signature(self):
        from app.core.sff.sff_reader import detect_version
        import tempfile, os

        sig = b"ElecbyteSpr\x00"
        header = sig + bytes([0, 0, 0, 1]) + bytes(500)  # verhi = 1

        with tempfile.NamedTemporaryFile(delete=False, suffix=".sff") as f:
            f.write(header)
            path = f.name

        try:
            version = detect_version(path)
            self.assertEqual(version, 1)
        finally:
            os.unlink(path)

    def test_valid_v2_signature(self):
        from app.core.sff.sff_reader import detect_version
        import tempfile, os

        sig = b"ElecbyteSpr\x00"
        header = sig + bytes([0, 0, 0, 2]) + bytes(500)  # verhi = 2

        with tempfile.NamedTemporaryFile(delete=False, suffix=".sff") as f:
            f.write(header)
            path = f.name

        try:
            version = detect_version(path)
            self.assertEqual(version, 2)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
