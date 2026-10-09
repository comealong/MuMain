"""Patch selected float vectors while preserving every other byte of a staged BMD."""
import math
import struct

from paths import workspace_path

from mu_art_pipeline.bmd import _Reader, _decrypt_v12, _encrypt_v12, parse_bmd


def patch_vector(reader, payload, values):
    if len(values) != 3 or not all(math.isfinite(value) for value in values):
        raise ValueError('A patched vector must have three finite coordinates')
    offset = reader.offset
    reader.read('3f')
    struct.pack_into('<3f', payload, offset, *values)


def patch_mesh(reader, payload, target):
    vertices, normals, uvs, triangles, _ = reader.read('5h')
    if vertices != len(target['vertices']) or normals != len(target['normals']):
        raise ValueError('Mesh layout changed')
    for vertex in target['vertices']:
        node = reader.read('h2x')[0]
        if node != vertex['node']:
            raise ValueError('Vertex node changed')
        patch_vector(reader, payload, vertex['position'])
    for normal in target['normals']:
        node = reader.read('h2x')[0]
        if node != normal['node']:
            raise ValueError('Normal node changed')
        patch_vector(reader, payload, normal['normal'])
        reader.read_bytes(4)
    reader.read_bytes(uvs * 8 + triangles * 64 + 32)


def patch_actions(reader, payload, target):
    for action in target['actions']:
        keys, locked = reader.read('hB')
        if (keys, bool(locked)) != (action['keys'], action['lock_positions']):
            raise ValueError('Action layout changed')
        if locked:
            for position in action['positions']:
                patch_vector(reader, payload, position)


def patch_bones(reader, payload, target):
    for bone in target['bones']:
        dummy = bool(reader.read('B')[0])
        if dummy != bone['dummy']:
            raise ValueError('Dummy bone changed')
        if dummy:
            continue
        reader.read_bytes(32)
        if reader.read('h')[0] != bone['parent']:
            raise ValueError('Bone parent changed')
        for action in bone['actions']:
            for position in action['positions']:
                patch_vector(reader, payload, position)
            reader.read_bytes(len(action['rotations']) * 12)


def write_patched_bmd(source, destination, target):
    destination = workspace_path(destination)
    parse_bmd(source)
    file_data = source.read_bytes()
    version = file_data[3]
    payload = bytearray(_decrypt_v12(file_data[8:]) if version == 12 else file_data[4:])
    reader = _Reader(payload)
    reader.read_bytes(32)
    meshes, bones, actions = reader.read('3h')
    if (meshes, bones, actions) != (len(target['meshes']), len(target['bones']), len(target['actions'])):
        raise ValueError('BMD layout changed')
    for mesh in target['meshes']:
        patch_mesh(reader, payload, mesh)
    patch_actions(reader, payload, target)
    patch_bones(reader, payload, target)
    encoded = bytes(payload)
    if version == 12:
        encoded = _encrypt_v12(encoded)
        encoded = b'BMD\x0c' + struct.pack('<i', len(encoded)) + encoded
    else:
        encoded = b'BMD\x0a' + encoded
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as output:
        output.write(encoded)
    return parse_bmd(destination)
