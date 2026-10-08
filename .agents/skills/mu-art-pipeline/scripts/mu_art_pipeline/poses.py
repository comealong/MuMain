"""Evaluate a shared MU BMD pose without requiring Blender."""
from __future__ import annotations

import math
from typing import Any

IDENTITY = ((1.0, 0.0, 0.0, 0.0), (0.0, 1.0, 0.0, 0.0),
            (0.0, 0.0, 1.0, 0.0), (0.0, 0.0, 0.0, 1.0))


def local_matrix(position: list[float], rotation: list[float]) -> list[list[float]]:
    """Return T @ Rz @ Ry @ Rx; BMD Euler angles are radians."""
    x, y, z = rotation
    cx, sx = math.cos(x), math.sin(x)
    cy, sy = math.cos(y), math.sin(y)
    cz, sz = math.cos(z), math.sin(z)
    return [
        [cz * cy, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx, position[0]],
        [sz * cy, sz * sy * sx + cz * cx, sz * sy * cx - cz * sx, position[1]],
        [-sy, cy * sx, cy * cx, position[2]],
        [0.0, 0.0, 0.0, 1.0],
    ]


def multiply_matrices(left, right) -> list[list[float]]:
    return [[sum(left[row][k] * right[k][column] for k in range(4))
             for column in range(4)] for row in range(4)]


def pose_matrices(model: dict[str, Any], action_index: int, key_index: int) -> list:
    """Resolve every bone's world matrix at one exact BMD action/key."""
    if not 0 <= action_index < len(model['actions']):
        raise ValueError(f'Invalid action index: {action_index}')
    if not 0 <= key_index < model['actions'][action_index]['keys']:
        raise ValueError(f'Invalid key index: {key_index}')
    bones = model['bones']
    matrices = [None] * len(bones)
    visiting = set()

    def resolve(index):
        if matrices[index] is not None:
            return matrices[index]
        if index in visiting:
            raise ValueError('BMD bone hierarchy contains a cycle')
        visiting.add(index)
        bone = bones[index]
        local = IDENTITY
        if not bone['dummy']:
            action = bone['actions'][action_index]
            local = local_matrix(action['positions'][key_index], action['rotations'][key_index])
        parent = bone['parent']
        matrices[index] = multiply_matrices(resolve(parent), local) if parent >= 0 else local
        visiting.remove(index)
        return matrices[index]

    return [resolve(index) for index in range(len(bones))]


def transform_position(matrix, position: list[float]) -> list[float]:
    return [sum(matrix[row][column] * position[column] for column in range(3))
            + matrix[row][3] for row in range(3)]


def transform_normal(matrix, normal: list[float]) -> list[float]:
    rotated = [sum(matrix[row][column] * normal[column] for column in range(3))
               for row in range(3)]
    length = math.hypot(*rotated) or 1.0
    return [value / length for value in rotated]


def validate_part_bones(part: dict[str, Any], player: dict[str, Any]) -> list[int]:
    """Check used bone indices and ancestors, ignoring unused helper bones."""
    nodes = {item['node'] for mesh in part['meshes']
             for field in ('vertices', 'normals') for item in mesh[field]}
    used = set(nodes)
    pending = list(nodes)
    while pending:
        index = pending.pop()
        if not 0 <= index < min(len(part['bones']), len(player['bones'])):
            raise ValueError(f'Bone {index} is absent from the shared skeleton')
        source, target = part['bones'][index], player['bones'][index]
        if (source['name'], source['parent'], source['dummy']) != (
                target['name'], target['parent'], target['dummy']):
            raise ValueError(f'Bone {index} does not match the shared skeleton')
        parent = source['parent']
        if parent >= 0 and parent not in used:
            used.add(parent)
            pending.append(parent)
    return sorted(nodes)
