"""Binary-format primitives shared by N64 sidecar converters."""
from __future__ import annotations

import struct

MASK24 = 0x00FFFFFF


def align_up(value: int, alignment: int) -> int:
    if alignment <= 0 or alignment & (alignment - 1):
        raise ValueError("alignment must be a positive power of two")
    return (value + alignment - 1) & ~(alignment - 1)


def be_u16(data: bytes | bytearray | memoryview, offset: int) -> int:
    return struct.unpack_from(">H", data, offset)[0]


def be_s16(data: bytes | bytearray | memoryview, offset: int) -> int:
    return struct.unpack_from(">h", data, offset)[0]


def be_u32(data: bytes | bytearray | memoryview, offset: int) -> int:
    return struct.unpack_from(">I", data, offset)[0]


def be_s32(data: bytes | bytearray | memoryview, offset: int) -> int:
    return struct.unpack_from(">i", data, offset)[0]


def be_offset24(data: bytes | bytearray | memoryview, offset: int) -> int:
    return be_u32(data, offset) & MASK24


def le_u16_bytes(value: int) -> bytes:
    return struct.pack("<H", value & 0xFFFF)


def le_u32_bytes(value: int) -> bytes:
    return struct.pack("<I", value & 0xFFFFFFFF)


def le_s32_bytes(value: int) -> bytes:
    return struct.pack("<i", value)
