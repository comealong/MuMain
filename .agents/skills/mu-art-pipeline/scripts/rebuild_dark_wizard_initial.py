"""Create an explicitly requested historical static snapshot; use create_dark_wizard_group.py for recovery."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from mu_art_pipeline.bmd import parse_bmd
from mu_art_pipeline.character_sources import ROOT, WORKSPACE, PARTS, stage_sources
from mu_art_pipeline.poses import (
    pose_matrices, transform_normal, transform_position, validate_part_bones,
)
from mu_art_pipeline.textures import convert_texture


ACTION_INDEX = 1
KEY_INDEX = 0
OBJECT_NAME = 'DarkWizard_Initial_Rebuilt'
TEXTURE_NAME = 'skin_barbarian_01.jpg'
MATERIAL_NAME = 'MU_Skin'
DECIMAL_PLACES = 7


def prepare_meshes(staged: Path, player: dict, matrices: list) -> list[dict]:
    parts = []
    for name in PARTS:
        part = parse_bmd(staged / (name + '.bmd'))
        nodes = validate_part_bones(part, player)
        for index, mesh in enumerate(part['meshes']):
            if mesh['texture'] != TEXTURE_NAME:
                raise ValueError(f'{name}: unexpected texture {mesh["texture"]}')
            group = name if len(part['meshes']) == 1 else f'{name}_mesh_{index:02}'
            positions = [transform_position(matrices[v['node']], v['position'])
                         for v in mesh['vertices']]
            normals = [transform_normal(matrices[n['node']], n['normal'])
                       for n in mesh['normals']]
            parts.append({'name': group, 'mesh': mesh, 'positions': positions,
                          'normals': normals, 'used_bones': nodes})
    return parts


def vector_line(prefix: str, values) -> str:
    return prefix + ' ' + ' '.join(f'{value:.{DECIMAL_PLACES}f}' for value in values)


def mesh_obj_lines(part: dict, offsets: list[int]) -> list[str]:
    mesh = part['mesh']
    lines = ['g ' + part['name'], 'usemtl ' + MATERIAL_NAME]
    lines.extend(vector_line('v', position) for position in part['positions'])
    lines.extend(vector_line('vt', (u, 1.0 - v)) for u, v in mesh['uvs'])
    lines.extend(vector_line('vn', normal) for normal in part['normals'])
    for triangle in mesh['triangles']:
        corners = zip(triangle['vertices'], triangle['uvs'], triangle['normals'])
        face = [f'{v + offsets[0]}/{uv + offsets[1]}/{n + offsets[2]}' for v, uv, n in corners]
        lines.append('f ' + ' '.join(face))
    for index, field in enumerate(('vertices', 'uvs', 'normals')):
        offsets[index] += len(mesh[field])
    return lines


def write_obj_bundle(output: Path, parts: list[dict]) -> Path:
    obj = output / (OBJECT_NAME + '.obj')
    mtl = obj.with_suffix('.mtl')
    lines = ['mtllib ' + mtl.name, 'o ' + OBJECT_NAME]
    offsets = [1, 1, 1]
    for part in parts:
        lines.extend(mesh_obj_lines(part, offsets))
    obj.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    material = [f'newmtl {MATERIAL_NAME}', 'Ka 1.0 1.0 1.0', 'Kd 1.0 1.0 1.0',
                'Ks 0.0 0.0 0.0', 'd 1.0', 'illum 1', f'map_Kd {TEXTURE_NAME}']
    mtl.write_text('\n'.join(material) + '\n', encoding='utf-8')
    convert_texture(output / 'sources/skin_barbarian_01.OZJ', output / TEXTURE_NAME)
    return obj


def part_summary(part: dict) -> dict:
    positions, mesh = part['positions'], part['mesh']
    return {'name': part['name'], 'vertices': len(positions), 'uvs': len(mesh['uvs']),
            'normals': len(mesh['normals']), 'faces': len(mesh['triangles']),
            'used_bones': part['used_bones'],
            'minimum': [min(p[i] for p in positions) for i in range(3)],
            'maximum': [max(p[i] for p in positions) for i in range(3)]}


def rebuild(source: Path, output: Path) -> dict:
    if not output.is_relative_to(WORKSPACE.resolve()):
        raise ValueError('Output must be inside tools/art_pipeline/workspace')
    if output.exists():
        raise FileExistsError(f'Choose a new output directory: {output}')
    hashes = stage_sources(source, output)
    staged = output / 'sources'
    player = parse_bmd(staged / 'player.bmd')
    matrices = pose_matrices(player, ACTION_INDEX, KEY_INDEX)
    parts = prepare_meshes(staged, player, matrices)
    obj = write_obj_bundle(output, parts)
    report = {
        'object': OBJECT_NAME, 'obj': str(obj), 'source_directory': str(source),
        'source_sha256': hashes, 'action_index': ACTION_INDEX, 'key_index': KEY_INDEX,
        'player_bones': len(player['bones']), 'player_actions': len(player['actions']),
        'pose_formula': 'global[parent] @ T(position) @ Rz(z) @ Ry(y) @ Rx(x)',
        'uv_convention': 'blender_bottom_left', 'reference_geometry_read': False,
        'parts': [part_summary(part) for part in parts], 'global_bone_matrices': matrices,
    }
    (output / 'rebuild_manifest.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--static-snapshot', action='store_true',
                        help='Explicitly request a merged static reference instead of character recovery')
    parser.add_argument('--source', type=Path, default=ROOT / 'src/bin/Data/Player')
    parser.add_argument('--output', type=Path, default=Path('reconstruction/dark_wizard_from_sources'),
                        help='New directory relative to tools/art_pipeline/workspace')
    args = parser.parse_args()
    if not args.static_snapshot:
        parser.error('Character recovery uses create_dark_wizard_group.py; '
                     'this historical tool requires --static-snapshot.')
    report = rebuild(args.source.resolve(), (WORKSPACE / args.output).resolve())
    print(json.dumps({key: value for key, value in report.items()
                      if key != 'global_bone_matrices'}, indent=2))


if __name__ == '__main__':
    main()
