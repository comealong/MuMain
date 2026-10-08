"""Blender worker for the source-only Dark Wizard shared skeleton workflow."""
from pathlib import Path
import json
import sys

import bpy

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mu_art_pipeline.bmd import parse_bmd
from mu_art_pipeline.poses import pose_matrices, transform_position
from mu_art_pipeline.blender_player_rig import (
    create_shared_armature, create_player_actions, select_player_action, store_player_metadata,
)
from mu_art_pipeline.blender_player_meshes import create_skin_material, create_body_parts
from mu_art_pipeline.blender_character_preview import set_preview_scene
from mu_art_pipeline.character_sources import PARTS, RESTORATION_MODE

GROUP_NAME = 'DarkWizard_Client_Group'
INITIAL_ACTION = 1
POSE_ERROR_LIMIT = 0.0002


def confirm_initial_binding(player, parts, objects):
    matrices = pose_matrices(player, INITIAL_ACTION, 0)
    dependency_graph = bpy.context.evaluated_depsgraph_get()
    reports = []
    for (part_name, part), obj in zip(parts, objects):
        source = part['meshes'][0]
        evaluated = obj.evaluated_get(dependency_graph).to_mesh()
        try:
            errors = [max(abs(actual - expected) for actual, expected in zip(vertex.co,
                      transform_position(matrices[record['node']], record['position'])))
                      for vertex, record in zip(evaluated.vertices, source['vertices'])]
            maximum = max(errors, default=0.0)
            if len(evaluated.vertices) != len(source['vertices']) or maximum > POSE_ERROR_LIMIT:
                raise ValueError(f'{part_name}: shared skeleton binding mismatch: {maximum}')
            reports.append({'part': part_name, 'object': obj.name, 'vertices': len(evaluated.vertices),
                            'faces': len(evaluated.polygons), 'initial_pose_maximum_error': maximum,
                            'shared_armature': obj.modifiers[0].object.name})
        finally:
            obj.evaluated_get(dependency_graph).to_mesh_clear()
    return reports


def set_group_presentation(rig, objects, collection):
    set_preview_scene(objects[0])
    rig.show_in_front = False
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                area.spaces.active.overlay.show_bones = False
                area.spaces.active.overlay.show_extras = False
    for obj in objects:
        obj['mu_character_source'] = 'Original Class01 BMD; shared Player action 1/key 0 initially'
    collection['mu_character_rig'] = rig.name


def build(output: Path):
    player = parse_bmd(output / 'sources/player.bmd')
    parts = [(name, parse_bmd(output / 'sources' / (name + '.bmd'))) for name in PARTS]
    if any(len(part['meshes']) != 1 for _, part in parts):
        raise ValueError('This Class01 workflow expects one mesh per body part')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    collection = bpy.data.collections.new(GROUP_NAME)
    bpy.context.scene.collection.children.link(collection)
    rig, names = create_shared_armature(player, collection, 'Player_Shared_Armature')
    material = create_skin_material(output / 'skin_barbarian_01.jpg')
    objects = create_body_parts(parts, player, rig, names, collection, material)
    actions = create_player_actions(player, rig, names)
    print("Actions complete; storing source metadata", flush=True)
    store_player_metadata(player, rig, names, actions, output / "player_source_metadata.json")
    print("Source metadata stored; selecting initial action", flush=True)
    select_player_action(rig, actions[INITIAL_ACTION])
    print("Initial action selected; checking binding", flush=True)
    reports = confirm_initial_binding(player, parts, objects)
    print("Binding confirmed; configuring preview", flush=True)
    set_group_presentation(rig, objects, collection)
    scene = bpy.context.scene
    scene['mu_character_group'] = GROUP_NAME
    collection['mu_restoration_mode'] = RESTORATION_MODE
    scene['mu_restoration_mode'] = RESTORATION_MODE
    scene['mu_action_index'] = INITIAL_ACTION
    scene.render.fps = 24
    report = {'restoration_mode': RESTORATION_MODE, 'merged_mesh': False,
              'group': GROUP_NAME, 'armatures': 1, 'bones': len(names), 'actions': len(actions),
              'initial_action': INITIAL_ACTION, 'initial_key': 0, 'separate_mesh_objects': len(objects),
              'parts': reports, 'reference_geometry_read': False, 'animation_fps': 24,
              'animation_note': 'BMD key i is Blender frame i+1. Runtime play speed is not baked.',
              'root_lock': 'Locked actions freeze root XY at key 0, BodyHeight=0',
              'source_metadata_text': rig['mu_bmd_source_text']}
    (output / 'group_manifest.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    scene.render.filepath = str(output / (GROUP_NAME + '.png'))
    bpy.ops.wm.save_as_mainfile(filepath=str(output / (GROUP_NAME + '.blend')))
    bpy.ops.render.render(write_still=True)
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    arguments = sys.argv[sys.argv.index('--') + 1:]
    if len(arguments) != 1:
        raise ValueError('Pass the newly staged output directory after --')
    target = Path(arguments[0]).resolve()
    if not target.is_relative_to((ROOT / 'tools/art_pipeline/workspace').resolve()):
        raise ValueError('Output must be in the art workspace')
    if (target / (GROUP_NAME + '.blend')).exists():
        raise FileExistsError('Group already exists')
    build(target)
