"""Preview an explicitly requested historical merged OBJ; character recovery uses create_dark_wizard_group.py."""
from pathlib import Path
import json
import sys

import bpy
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mu_art_pipeline.blender_character_preview import set_preview_scene

ROOT = Path(__file__).resolve().parents[4]
WORKSPACE = (ROOT / 'tools/art_pipeline/workspace').resolve()


def output_paths() -> tuple[Path, Path]:
    arguments = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    if len(arguments) != 1:
        raise ValueError('Pass one rebuilt OBJ path after --')
    source = Path(arguments[0]).resolve()
    if not source.is_relative_to(WORKSPACE) or source.suffix.lower() != '.obj':
        raise ValueError('Expected an OBJ inside the art workspace')
    if not source.is_file():
        raise FileNotFoundError(source)
    destination = source.with_suffix('.blend')
    if destination.exists() or source.with_suffix('.png').exists():
        raise FileExistsError('Preview outputs already exist; choose a new rebuild directory')
    return source, destination


def import_mesh(source: Path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.obj_import(filepath=str(source), forward_axis='Y', up_axis='Z',
                          use_split_objects=False, use_split_groups=False)
    obj = bpy.context.active_object
    obj['mu_bmd_uv_convention'] = 'blender_bottom_left'
    obj['mu_pose_source'] = 'player.bmd action_index=1 key_index=0; static bake'
    for material in obj.data.materials:
        for node in material.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                material.node_tree.nodes.active = node
                node.image.pack()
    return obj


def main():
    source, destination = output_paths()
    obj = import_mesh(source)
    set_preview_scene(obj)
    bpy.context.scene.render.filepath = str(source.with_suffix('.png'))
    bpy.ops.wm.save_as_mainfile(filepath=str(destination))
    bpy.ops.render.render(write_still=True)
    print(json.dumps({'blend': str(destination), 'vertices': len(obj.data.vertices),
                      'faces': len(obj.data.polygons), 'packed_texture': True}))


if __name__ == '__main__':
    main()

