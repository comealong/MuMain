"""Readers and writers for the MuMain terrain map files."""
from __future__ import annotations
from dataclasses import dataclass
import struct
from pathlib import Path

SIZE = 256
CELLS = SIZE * SIZE
XOR_KEY = bytes((0xD1,0x73,0x52,0xF6,0xD2,0x9A,0xCB,0x27,0x3E,0xAF,0x59,0x31,0x37,0xB3,0xE7,0xA2))
BUX_KEY = bytes((0xFC,0xCF,0xAB))
OBJECT_RECORD = struct.Struct("<h3f3ff")

@dataclass
class TerrainMap:
    version: int
    map_number: int
    layer1: bytearray
    layer2: bytearray
    alpha: bytearray

@dataclass
class TerrainAttributes:
    version: int
    map_number: int
    width: int
    height: int
    values: bytearray
    bytes_per_cell: int

@dataclass
class MapObject:
    type_id: int
    x: float
    y: float
    z: float
    angle_x: float
    angle_y: float
    angle_z: float
    scale: float

def map_decrypt(data: bytes) -> bytes:
    out = bytearray(len(data)); key = 0x5E
    for i, value in enumerate(data):
        out[i] = ((value ^ XOR_KEY[i % 16]) - key) & 0xFF
        key = (value + 0x3D) & 0xFF
    return bytes(out)

def map_encrypt(data: bytes) -> bytes:
    out = bytearray(len(data)); key = 0x5E
    for i, value in enumerate(data):
        out[i] = ((value + key) & 0xFF) ^ XOR_KEY[i % 16]
        key = (out[i] + 0x3D) & 0xFF
    return bytes(out)

def bux(data: bytes) -> bytes:
    return bytes(value ^ BUX_KEY[i % 3] for i, value in enumerate(data))

def read_mapping(path: Path) -> TerrainMap:
    raw = map_decrypt(path.read_bytes())
    if len(raw) != 2 + CELLS * 3:
        raise ValueError(f"{path.name}: unexpected decrypted mapping size ({len(raw)} bytes).")
    return TerrainMap(raw[0], raw[1], bytearray(raw[2:2+CELLS]),
                      bytearray(raw[2+CELLS:2+CELLS*2]), bytearray(raw[2+CELLS*2:]))

def write_mapping(path: Path, terrain: TerrainMap) -> None:
    if any(len(row) != CELLS for row in (terrain.layer1, terrain.layer2, terrain.alpha)):
        raise ValueError("Mapping layers must each contain exactly 256×256 cells.")
    header = bytes((terrain.version & 255, terrain.map_number & 255))
    path.write_bytes(map_encrypt(header + bytes(terrain.layer1) + bytes(terrain.layer2) + bytes(terrain.alpha)))

def read_attributes(path: Path) -> TerrainAttributes:
    raw = bux(map_decrypt(path.read_bytes()))
    if len(raw) == 4 + CELLS:
        width, values = 1, bytearray(raw[4:])
    elif len(raw) == 4 + CELLS * 2:
        width, values = 2, bytearray(raw[4::2])
    else:
        raise ValueError(f"{path.name}: unsupported decrypted attribute size ({len(raw)} bytes).")
    if raw[0] != 0 or raw[2:4] != b"\xff\xff":
        raise ValueError(f"{path.name}: unsupported attribute header {raw[:4].hex(' ')}.")
    if any(value >= 128 for value in values):
        raise ValueError(f"{path.name}: contains values rejected by the client loader.")
    return TerrainAttributes(raw[0], raw[1], raw[2], raw[3], values, width)

def write_attributes(path: Path, attrs: TerrainAttributes) -> None:
    if len(attrs.values) != CELLS:
        raise ValueError("Attributes must contain exactly 256×256 cells.")
    header = bytes((attrs.version & 255, attrs.map_number & 255, attrs.width & 255, attrs.height & 255))
    body = b"".join(struct.pack("<H", v) for v in attrs.values) if attrs.bytes_per_cell == 2 else bytes(attrs.values)
    path.write_bytes(map_encrypt(bux(header + body)))

def read_server_attributes(path: Path) -> tuple[bytes, bytearray]:
    raw = path.read_bytes()
    if len(raw) != 3 + CELLS:
        raise ValueError(f"Expected 65,539-byte server TerrainData, found {len(raw)} bytes.")
    if list(raw[:3]) != [0, 255, 255]:
        raise ValueError("Unexpected server TerrainData header; expected 00 FF FF.")
    values = bytearray(raw[3:])
    if any(v >= 128 for v in values):
        raise ValueError("This looks encrypted; choose server TerrainData downloaded from the Admin Panel.")
    return raw[:3], values

def write_server_attributes(path: Path, base: bytes, values: bytearray, baseline: bytearray, edited: bytearray) -> int:
    if len(base) != 3 + CELLS or any(len(a) != CELLS for a in (values, baseline, edited)):
        raise ValueError("Server TerrainData and attribute arrays have unexpected sizes.")
    out = bytearray(base); changed = 0
    for i in range(CELLS):
        if edited[i] and values[i] != baseline[i]:
            out[3+i] = values[i] & ~0x02
            changed += 1
    path.write_bytes(out)
    return changed

def read_height(path: Path) -> tuple[bytearray, bytes, bytes]:
    raw = path.read_bytes(); expected = 4 + 1080 + CELLS
    if len(raw) < expected:
        raise ValueError(f"{path.name}: expected at least {expected} bytes, found {len(raw)}.")
    pixels = raw[1084:expected]; values = bytearray(CELLS)
    for y in range(SIZE):
        values[y*SIZE:(y+1)*SIZE] = pixels[y*SIZE:(y+1)*SIZE]
    return values, raw[:4], raw[4:1084]

def write_height(path: Path, values: bytearray, prefix: bytes, header: bytes) -> None:
    if len(values) != CELLS or len(prefix) != 4 or len(header) != 1080:
        raise ValueError("Unexpected height map dimensions or header sizes.")
    pixels = bytearray(CELLS)
    for y in range(SIZE):
        pixels[y*SIZE:(y+1)*SIZE] = bytes(min(255, max(0, values[y*SIZE+x])) for x in range(SIZE))
    path.write_bytes(prefix + header + pixels)

def read_objects(path: Path) -> tuple[int, int, list[MapObject]]:
    raw = map_decrypt(path.read_bytes())
    if len(raw) < 4: raise ValueError(f"{path.name}: object header is truncated.")
    version, number, count = struct.unpack_from("<BBH", raw)
    if len(raw) != 4 + count * OBJECT_RECORD.size:
        raise ValueError(f"{path.name}: object count does not match file size.")
    objects = []
    for i in range(count):
        row = OBJECT_RECORD.unpack_from(raw, 4 + i * OBJECT_RECORD.size)
        objects.append(MapObject(row[0], *row[1:]))
    return version, number, objects

def write_objects(path: Path, version: int, number: int, objects: list[MapObject]) -> None:
    if len(objects) > 65535: raise ValueError("A map cannot contain more than 65,535 objects.")
    raw = bytearray(struct.pack("<BBH", version & 255, number & 255, len(objects)))
    for obj in objects:
        raw.extend(OBJECT_RECORD.pack(obj.type_id, obj.x, obj.y, obj.z, obj.angle_x, obj.angle_y, obj.angle_z, obj.scale))
    path.write_bytes(map_encrypt(raw))
