"""Read MU Online model BMD v10/v12 files used by this client."""

from __future__ import annotations

import math
import struct
from pathlib import Path
from typing import Any


MAX_BMD_BYTES = 512 * 1024 * 1024
MAX_MESHES = 50
MAX_BONES = 200
MAX_ACTIONS = 512
MAX_VERTICES = 15000
MAX_TRIANGLES = 30000
TRIANGLE_BYTES = 64
_MAP_XOR_KEY = bytes((0xD1, 0x73, 0x52, 0xF6, 0xD2, 0x9A, 0xCB, 0x27,
                      0x3E, 0xAF, 0x59, 0x31, 0x37, 0xB3, 0xE7, 0xA2))


class _Reader:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.offset = 0

    def read(self, format_string: str) -> tuple[Any, ...]:
        layout = struct.Struct("<" + format_string)
        self.require(layout.size)
        values = layout.unpack_from(self.data, self.offset)
        self.offset += layout.size
        return values

    def read_bytes(self, count: int) -> bytes:
        self.require(count)
        result = self.data[self.offset:self.offset + count]
        self.offset += count
        return result

    def read_name(self, count: int) -> str:
        return self.read_bytes(count).split(b"\0", 1)[0].decode("utf-8", errors="replace")

    def require(self, count: int) -> None:
        if count < 0 or self.offset + count > len(self.data):
            raise ValueError(f"Truncated BMD data at byte offset {self.offset}.")


def _decrypt_v12(encrypted: bytes) -> bytes:
    key = 0x5E
    output = bytearray(len(encrypted))
    for index, value in enumerate(encrypted):
        output[index] = ((value ^ _MAP_XOR_KEY[index % len(_MAP_XOR_KEY)]) - key) & 0xFF
        key = (value + 0x3D) & 0xFF
    return bytes(output)


def _bounded_count(value: int, maximum: int, label: str) -> int:
    if value < 0 or value > maximum:
        raise ValueError(f"Invalid BMD {label} count: {value}.")
    return value


def _read_mesh(reader: _Reader, mesh_index: int, bone_count: int) -> dict[str, Any]:
    vertex_count, normal_count, uv_count, triangle_count, texture_index = reader.read("5h")
    _bounded_count(vertex_count, MAX_VERTICES, f"mesh {mesh_index} vertex")
    _bounded_count(normal_count, MAX_VERTICES, f"mesh {mesh_index} normal")
    _bounded_count(uv_count, MAX_VERTICES, f"mesh {mesh_index} UV")
    _bounded_count(triangle_count, MAX_TRIANGLES, f"mesh {mesh_index} triangle")

    vertices = []
    for _ in range(vertex_count):
        node, x, y, z = reader.read("h2xfff")
        if bone_count and not 0 <= node < bone_count:
            raise ValueError(f"Invalid bone index {node} in mesh {mesh_index}.")
        if not all(math.isfinite(value) for value in (x, y, z)):
            raise ValueError(f"Non-finite vertex in mesh {mesh_index}.")
        vertices.append({"node": node, "position": [x, y, z]})

    normals = []
    for _ in range(normal_count):
        node, x, y, z, bind_vertex = reader.read("h2xfffh2x")
        if bone_count and not 0 <= node < bone_count:
            raise ValueError(f"Invalid normal bone index {node} in mesh {mesh_index}.")
        normals.append({"node": node, "normal": [x, y, z], "bind_vertex": bind_vertex})

    uvs = [list(reader.read("2f")) for _ in range(uv_count)]
    triangles = []
    for triangle_index in range(triangle_count):
        triangle = reader.read_bytes(TRIANGLE_BYTES)
        polygon = triangle[0]
        if polygon not in (3, 4):
            raise ValueError(f"Invalid polygon size in mesh {mesh_index}, triangle {triangle_index}.")
        vertex_indices = list(struct.unpack_from("<4h", triangle, 2))
        normal_indices = list(struct.unpack_from("<4h", triangle, 10))
        uv_indices = list(struct.unpack_from("<4h", triangle, 18))
        for corner in range(polygon):
            if not 0 <= vertex_indices[corner] < vertex_count:
                raise ValueError(f"Invalid vertex index in mesh {mesh_index}, triangle {triangle_index}.")
            if not 0 <= normal_indices[corner] < normal_count:
                raise ValueError(f"Invalid normal index in mesh {mesh_index}, triangle {triangle_index}.")
            if not 0 <= uv_indices[corner] < uv_count:
                raise ValueError(f"Invalid UV index in mesh {mesh_index}, triangle {triangle_index}.")
        lightmap_uvs = [list(struct.unpack_from("<2f", triangle, 28 + 8 * corner)) for corner in range(4)]
        lightmap_index = struct.unpack_from("<h", triangle, 60)[0]
        triangles.append({
            "size": polygon,
            "vertices": vertex_indices[:polygon],
            "normals": normal_indices[:polygon],
            "uvs": uv_indices[:polygon],
            "lightmap_uvs": lightmap_uvs,
            "lightmap_index": lightmap_index,
        })

    texture_name = reader.read_name(32)
    return {
        "texture_index": texture_index,
        "texture": texture_name,
        "vertices": vertices,
        "normals": normals,
        "uvs": uvs,
        "triangles": triangles,
    }


def parse_bmd(path: Path) -> dict[str, Any]:
    """Parse the client's unencrypted v10 or encrypted v12 model format."""
    source = path.resolve()
    if not source.is_file():
        raise FileNotFoundError(f"BMD file not found: {source}")
    if source.stat().st_size > MAX_BMD_BYTES:
        raise ValueError(f"BMD exceeds the {MAX_BMD_BYTES // (1024 * 1024)} MiB size limit.")

    file_data = source.read_bytes()
    if len(file_data) < 4 or file_data[:3] != b"BMD":
        raise ValueError("Invalid MU Online BMD header.")
    version = file_data[3]
    if version == 0x0A:
        payload = file_data[4:]
    elif version == 0x0C:
        if len(file_data) < 8:
            raise ValueError("Encrypted BMD header is truncated.")
        encrypted_size = struct.unpack_from("<i", file_data, 4)[0]
        if encrypted_size < 0 or encrypted_size != len(file_data) - 8:
            raise ValueError("Invalid encrypted BMD payload size.")
        payload = _decrypt_v12(file_data[8:])
    else:
        raise ValueError(f"Unsupported client BMD version 0x{version:02X}; supported versions are 0x0A and 0x0C.")

    reader = _Reader(payload)
    name = reader.read_name(32)
    mesh_count = _bounded_count(reader.read("h")[0], MAX_MESHES, "mesh")
    bone_count = _bounded_count(reader.read("h")[0], MAX_BONES, "bone")
    action_count = _bounded_count(reader.read("h")[0], MAX_ACTIONS, "action")
    meshes = [_read_mesh(reader, index, bone_count) for index in range(mesh_count)]

    actions = []
    for action_index in range(action_count):
        key_count = _bounded_count(reader.read("h")[0], 10000, f"action {action_index} key")
        lock_positions = bool(reader.read("B")[0])
        positions = [list(reader.read("3f")) for _ in range(key_count)] if lock_positions else []
        actions.append({"keys": key_count, "lock_positions": lock_positions, "positions": positions})

    bones = []
    for bone_index in range(bone_count):
        is_dummy = bool(reader.read("B")[0])
        if is_dummy:
            bones.append({"name": f"dummy_{bone_index}", "parent": -1, "dummy": True, "actions": []})
            continue

        raw_bone_name = reader.read_bytes(32)
        bone_name = raw_bone_name.split(b"\0", 1)[0].decode("utf-8", errors="replace")
        parent = reader.read("h")[0]
        if parent < -1 or parent >= bone_count or parent == bone_index:
            raise ValueError(f"Invalid parent index {parent} for bone {bone_index}.")
        bone_actions = []
        for action in actions:
            keys = action["keys"]
            positions = [list(reader.read("3f")) for _ in range(keys)]
            rotations = [list(reader.read("3f")) for _ in range(keys)]
            bone_actions.append({"positions": positions, "rotations": rotations})
        bones.append({"name": bone_name or f"bone_{bone_index}", "raw_name": raw_bone_name.hex(),
                      "parent": parent, "dummy": False, "actions": bone_actions})

    if reader.offset > len(payload):
        raise ValueError("BMD parser moved beyond the decoded payload.")
    return {
        "version": version,
        "name": name,
        "meshes": meshes,
        "bones": bones,
        "actions": actions,
    }


def _fixed_ascii_name(value: str, label: str, suffix: str = '') -> bytes:
    encoded = (value + suffix).encode('ascii')
    if not encoded or len(encoded) >= 32 or b'\0' in encoded:
        raise ValueError(f"{label} must be an ASCII name shorter than 32 bytes.")
    return encoded.ljust(32, b'\0')



def _encode_mesh(mesh: dict[str, Any], mesh_index: int, bone_count: int) -> bytes:
    vertices = mesh.get('vertices', [])
    normals = mesh.get('normals', [])
    uvs = mesh.get('uvs', [])
    triangles = mesh.get('triangles', [])
    if not 0 < len(vertices) <= MAX_VERTICES:
        raise ValueError(f"Invalid mesh {mesh_index} vertex count: {len(vertices)}.")
    for values, maximum, label in ((normals, MAX_VERTICES, 'normal'), (uvs, MAX_VERTICES, 'UV'),
                                   (triangles, MAX_TRIANGLES, 'triangle')):
        if not 0 <= len(values) <= maximum:
            raise ValueError(f"Invalid mesh {mesh_index} {label} count: {len(values)}.")

    output = bytearray()
    texture_index = mesh.get('texture_index', 0)
    output.extend(struct.pack('<5h', len(vertices), len(normals), len(uvs), len(triangles), texture_index))
    for vertex in vertices:
        position = vertex.get('position', ())
        if len(position) != 3 or not all(math.isfinite(float(axis)) for axis in position):
            raise ValueError(f"Invalid vertex position in mesh {mesh_index}.")
        node = vertex.get('node', 0)
        if not isinstance(node, int) or not 0 <= node < bone_count:
            raise ValueError(f"Invalid vertex bone index in mesh {mesh_index}.")
        output.extend(struct.pack('<h2xfff', node, *(float(axis) for axis in position)))
    for normal in normals:
        node = normal.get('node', 0) if isinstance(normal, dict) else 0
        values = normal.get('normal', ()) if isinstance(normal, dict) else normal
        bind_vertex = normal.get('bind_vertex', 0) if isinstance(normal, dict) else 0
        _validate_vector(values, 3, f"mesh {mesh_index} normal")
        if not isinstance(node, int) or not 0 <= node < bone_count:
            raise ValueError(f"Invalid normal bone index in mesh {mesh_index}.")
        output.extend(struct.pack('<h2xfffh2x', node, *(float(axis) for axis in values), int(bind_vertex)))
    for uv in uvs:
        if len(uv) != 2 or not all(math.isfinite(float(axis)) for axis in uv):
            raise ValueError(f"Invalid UV in mesh {mesh_index}.")
        output.extend(struct.pack('<2f', *(float(axis) for axis in uv)))

    for triangle_index, triangle in enumerate(triangles):
        polygon = int(triangle.get('size', 0))
        indices = []
        for field in ('vertices', 'normals', 'uvs'):
            values = triangle.get(field, [])
            if polygon not in (3, 4) or len(values) != polygon:
                raise ValueError(f"Invalid polygon data in mesh {mesh_index}, triangle {triangle_index}.")
            limit = {'vertices': len(vertices), 'normals': len(normals), 'uvs': len(uvs)}[field]
            if any(not isinstance(index, int) or not 0 <= index < limit for index in values):
                raise ValueError(f"Invalid {field} index in mesh {mesh_index}, triangle {triangle_index}.")
            indices.append(list(values) + [0] * (4 - polygon))
        triangle_data = bytearray(64)
        struct.pack_into('<B', triangle_data, 0, polygon)
        struct.pack_into('<4h', triangle_data, 2, *indices[0])
        struct.pack_into('<4h', triangle_data, 10, *indices[1])
        struct.pack_into('<4h', triangle_data, 18, *indices[2])
        lightmap_uvs = triangle.get('lightmap_uvs', [[0.0, 0.0]] * 4)
        if len(lightmap_uvs) != 4:
            raise ValueError(f"Invalid lightmap UVs in mesh {mesh_index}, triangle {triangle_index}.")
        for corner, uv in enumerate(lightmap_uvs):
            _validate_vector(uv, 2, f"mesh {mesh_index} lightmap UV")
            struct.pack_into('<2f', triangle_data, 28 + 8 * corner, *(float(value) for value in uv))
        struct.pack_into('<h', triangle_data, 60, int(triangle.get('lightmap_index', 0)))
        output.extend(triangle_data)

    texture = mesh.get('texture', '')
    output.extend(_fixed_ascii_name(texture, f"mesh {mesh_index} texture") if texture else bytes(32))
    return bytes(output)


def encode_static_bmd_v12(name: str, meshes: list[dict[str, Any]]) -> bytes:
    """Encode static mesh geometry as the client's encrypted v12 BMD format."""
    bones = [{"name": "Root", "parent": -1, "dummy": False, "actions": [{
        "positions": [[0.0, 0.0, 0.0]], "rotations": [[0.0, 0.0, 0.0]],
    }]}]
    actions = [{"keys": 1, "lock_positions": False, "positions": []}]
    return encode_bmd_v12(name, meshes, bones, actions)


def encode_bmd_v12(
    name: str,
    meshes: list[dict[str, Any]],
    bones: list[dict[str, Any]],
    actions: list[dict[str, Any]],
) -> bytes:
    """Encode mesh, bone, and action data as the client's encrypted v12 BMD format."""
    if not meshes or len(meshes) > MAX_MESHES:
        raise ValueError(f"A BMD must contain 1 to {MAX_MESHES} meshes.")
    if not bones or len(bones) > MAX_BONES:
        raise ValueError(f"A BMD must contain 1 to {MAX_BONES} bones.")
    if not actions or len(actions) > MAX_ACTIONS:
        raise ValueError(f"A BMD must contain 1 to {MAX_ACTIONS} actions.")

    model_name = Path(name).stem
    payload = bytearray(_fixed_ascii_name(model_name, 'model name', '.smd'))
    payload.extend(struct.pack('<3h', len(meshes), len(bones), len(actions)))
    for mesh_index, mesh in enumerate(meshes):
        payload.extend(_encode_mesh(mesh, mesh_index, len(bones)))

    for action_index, action in enumerate(actions):
        key_count = action.get('keys', 0)
        lock_positions = bool(action.get('lock_positions', False))
        if not isinstance(key_count, int) or not 0 <= key_count <= 10000:
            raise ValueError(f"Invalid BMD action {action_index} key count: {key_count}.")
        payload.extend(struct.pack('<hB', key_count, lock_positions))
        positions = action.get('positions', [])
        if lock_positions:
            if len(positions) != key_count:
                raise ValueError(f"Invalid locked positions for BMD action {action_index}.")
            for position in positions:
                _validate_vector(position, 3, f"action {action_index} position")
                payload.extend(struct.pack('<3f', *(float(value) for value in position)))

    for bone_index, bone in enumerate(bones):
        is_dummy = bool(bone.get('dummy', False))
        payload.extend(struct.pack('<B', is_dummy))
        if is_dummy:
            continue
        raw_name = bone.get('raw_name')
        if raw_name:
            name_bytes = bytes.fromhex(raw_name)
            if len(name_bytes) != 32:
                raise ValueError(f"Invalid preserved name bytes for BMD bone {bone_index}.")
            payload.extend(name_bytes)
        else:
            payload.extend(_fixed_ascii_name(bone.get('name', f"bone_{bone_index}"), f"bone {bone_index} name"))
        parent = bone.get('parent', -1)
        if not isinstance(parent, int) or parent < -1 or parent >= len(bones) or parent == bone_index:
            raise ValueError(f"Invalid parent index for BMD bone {bone_index}.")
        payload.extend(struct.pack('<h', parent))
        bone_actions = bone.get('actions', [])
        if len(bone_actions) != len(actions):
            raise ValueError(f"BMD bone {bone_index} must contain data for each action.")
        for action_index, action in enumerate(actions):
            key_count = action['keys']
            bone_action = bone_actions[action_index]
            positions = bone_action.get('positions', [])
            rotations = bone_action.get('rotations', [])
            if len(positions) != key_count or len(rotations) != key_count:
                raise ValueError(f"Invalid animation keys for BMD bone {bone_index}, action {action_index}.")
            for position in positions:
                _validate_vector(position, 3, f"bone {bone_index} position")
                payload.extend(struct.pack('<3f', *(float(value) for value in position)))
            for rotation in rotations:
                _validate_vector(rotation, 3, f"bone {bone_index} rotation")
                payload.extend(struct.pack('<3f', *(float(value) for value in rotation)))

    encrypted = _encrypt_v12(bytes(payload))
    return b'BMD\x0c' + struct.pack('<i', len(encrypted)) + encrypted


def _validate_vector(values: Any, size: int, label: str) -> None:
    if len(values) != size or not all(math.isfinite(float(value)) for value in values):
        raise ValueError(f"Invalid {label} vector.")


def _encrypt_v12(plain: bytes) -> bytes:
    key = 0x5E
    output = bytearray(len(plain))
    for index, value in enumerate(plain):
        encrypted = ((value + key) & 0xFF) ^ _MAP_XOR_KEY[index % len(_MAP_XOR_KEY)]
        output[index] = encrypted
        key = (encrypted + 0x3D) & 0xFF
    return bytes(output)
