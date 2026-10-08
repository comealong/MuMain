"""Compare an already rebuilt OBJ with a reference without modifying either file."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

VERTEX_TOLERANCE = 1e-7
UV_TOLERANCE = 1e-7


def read_groups(path: Path) -> dict:
    groups = {}
    group = None
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        fields = line.split()
        if not fields:
            continue
        if fields[0] == 'g':
            group = ' '.join(fields[1:])
            if group in groups:
                raise ValueError(f'Duplicate group: {group}')
            groups[group] = {key: [] for key in ('v', 'vt', 'vn', 'f')}
        elif fields[0] in ('v', 'vt', 'vn', 'f'):
            if group is None:
                raise ValueError('Expected grouped OBJ records')
            key = fields[0]
            value = fields[1:] if key == 'f' else [float(v) for v in fields[1:]]
            groups[group][key].append(value)
    if not groups:
        raise ValueError(f'No mesh groups: {path}')
    return groups


def maximum_error(left: list, right: list) -> float:
    if len(left) != len(right) or any(len(a) != len(b) for a, b in zip(left, right)):
        raise ValueError('OBJ record counts differ')
    return max((abs(a - b) for x, y in zip(left, right) for a, b in zip(x, y)), default=0.0)


def compare(rebuilt: Path, reference: Path) -> dict:
    actual, expected = read_groups(rebuilt), read_groups(reference)
    if list(actual) != list(expected):
        raise ValueError('Group names or ordering differ')
    results = []
    for name, group in actual.items():
        other = expected[name]
        vertices = maximum_error(group['v'], other['v'])
        uvs = maximum_error(group['vt'], other['vt'])
        normals = maximum_error(group['vn'], other['vn'])
        topology_equal = group['f'] == other['f']
        results.append({'group': name, 'vertices': len(group['v']), 'faces': len(group['f']),
                        'maximum_vertex_coordinate_error': vertices,
                        'maximum_uv_error': uvs, 'maximum_normal_error': normals,
                        'face_vertex_uv_normal_indices_equal': topology_equal,
                        'passed': topology_equal and vertices <= VERTEX_TOLERANCE
                                  and uvs <= UV_TOLERANCE and normals <= VERTEX_TOLERANCE})
    return {'rebuilt': str(rebuilt), 'reference': str(reference), 'read_only_comparison': True,
            'sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (rebuilt, reference)},
            'parts': results, 'passed': all(item['passed'] for item in results)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rebuilt', type=Path)
    parser.add_argument('reference', type=Path)
    args = parser.parse_args()
    report = compare(args.rebuilt.resolve(), args.reference.resolve())
    print(json.dumps(report, indent=2))
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
