from __future__ import annotations

import unittest

from tools.n64_portlib.binary import (
    MASK24,
    align_up,
    be_offset24,
    be_s16,
    be_s32,
    be_u16,
    be_u32,
    le_s32_bytes,
    le_u16_bytes,
    le_u32_bytes,
)


class BinaryPrimitiveTests(unittest.TestCase):
    def test_big_endian_reads(self) -> None:
        data = bytes.fromhex("1234 fedc 89abcdef fffffffe 0f654321")
        self.assertEqual(be_u16(data, 0), 0x1234)
        self.assertEqual(be_s16(data, 2), -0x124)
        self.assertEqual(be_u32(data, 4), 0x89ABCDEF)
        self.assertEqual(be_s32(data, 8), -2)
        self.assertEqual(be_offset24(data, 12), 0x654321)

    def test_little_endian_writes(self) -> None:
        self.assertEqual(le_u16_bytes(0x1234), bytes.fromhex("3412"))
        self.assertEqual(le_u16_bytes(-1), bytes.fromhex("ffff"))
        self.assertEqual(le_u32_bytes(0x89ABCDEF), bytes.fromhex("efcdab89"))
        self.assertEqual(le_u32_bytes(-1), bytes.fromhex("ffffffff"))
        self.assertEqual(le_s32_bytes(-2), bytes.fromhex("feffffff"))

    def test_alignment(self) -> None:
        self.assertEqual(align_up(0, 16), 0)
        self.assertEqual(align_up(1, 16), 16)
        self.assertEqual(align_up(16, 16), 16)
        self.assertEqual(align_up(17, 16), 32)
        with self.assertRaises(ValueError):
            align_up(3, 3)

    def test_mask_constant(self) -> None:
        self.assertEqual(MASK24, 0x00FFFFFF)


if __name__ == "__main__":
    unittest.main()
