"""Build an isolated, reproducible dwarf sample from staged original MU assets."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import ROOT, experiment_from_arguments

EXPERIMENT = experiment_from_arguments()
from mu_art_pipeline.bmd import parse_bmd
from mu_art_pipeline.player_actions import extract_player_actions
from mu_art_pipeline.poses import validate_part_bones
from mu_art_pipeline.character_sources import PARTS
from mu_art_pipeline.blender_player_rig import (
    create_shared_armature, create_player_actions, select_player_action,
    store_player_metadata, bone_basis_samples,
)
from mu_art_pipeline.blender_player_meshes import create_skin_material, create_body_parts
from dwarf_geometry import (
    adapt_bone_positions, adapt_meshes, ground_alignment, lift_root,
    posed_vertices, confirm_preserved_data, confirm_finite_animation,
)
from bmd_patch import write_patched_bmd

from weapon_attachment import (
    RIGHT_WEAPON_NODE as SOCKET_NODE, ATTACHMENT_MODE, runtime_matrices,
    validate_sword_socket, client_held_weapon_vertices,
)
BINDING_TOLERANCE = 0.001
PREVIEW_POSES = (
    ('standing', 4, 0), ('walk', 17, 3), ('run', 26, 3),
    ('sword_windup', 39, 1), ('sword_swing', 39, 4), ('sword_followthrough', 40, 3),
)
GROUND_ADAPTED_ACTIONS = (4, 17, 26)
ORIGINAL_LOCATION = (-82.0, 0.0, 0.0)
DWARF_LOCATION = (82.0, 0.0, 0.0)


def hash_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes():
    names = ['player.bmd', *(name + '.bmd' for name in PARTS), 'skin_barbarian_01.OZJ']
    paths = [ROOT / 'src/bin/Data/Player' / name for name in names]
    paths += [ROOT / 'src/bin/Data/Item/Sword01.bmd', ROOT / 'src/bin/Data/Item/sword02.OZJ']
    return {str(path.relative_to(ROOT)): hash_file(path) for path in paths}


def correct_contact_heights(source, target, source_parts, target_parts, profile):
    old_boots, new_boots = source_parts[-1:], target_parts[-1:]
    floor = posed_vertices(source, old_boots, 4, 0)[:, 2].min()
    reports = []
    for index in GROUND_ADAPTED_ACTIONS:
        deltas = []
        for key in range(source['actions'][index]['keys']):
            old_min = posed_vertices(source, old_boots, index, key)[:, 2].min()
            new_min = posed_vertices(target, new_boots, index, key)[:, 2].min()
            offset = float(floor + (old_min - floor) * profile['leg_length'] - new_min)
            target['bones'][0]['actions'][index]['positions'][key][2] += offset
            if target['actions'][index]['lock_positions']:
                target['actions'][index]['positions'][key][2] += offset
            deltas.append(offset)
        reports.append({'action': index, 'root_z_corrections': deltas})
    return reports


def write_bundle(output, player, parts):
    destination = output / 'generated'
    reports = []
    models = [('player', player), *parts]
    for name, model in models:
        source = EXPERIMENT / 'sources' / (name + '.bmd')
        target = destination / 'Player' / source.name
        reopened = write_patched_bmd(source, target, model)
        rotation_keys = confirm_preserved_data(parse_bmd(source), reopened)
        for old_mesh, new_mesh in zip(model['meshes'], reopened['meshes']):
            for field in ('uvs', 'triangles', 'texture'):
                if old_mesh[field] != new_mesh[field]:
                    raise ValueError('UV/topology/texture changed')
        reports.append({'file': str(target.relative_to(output)), 'rotation_keys_preserved': rotation_keys})
    item_directory = destination / 'Item'
    item_directory.mkdir()
    for name in ('Sword01.bmd', 'sword02.OZJ'):
        shutil.copy2(EXPERIMENT / 'sources/item' / name, item_directory / name)
    shutil.copy2(EXPERIMENT / 'sources/skin_barbarian_01.OZJ', destination / 'Player/skin_barbarian_01.OZJ')
    return reports


def make_actor(player, parts, name, location, material):
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    rig, names = create_shared_armature(player, collection, name + '_Armature')
    objects = create_body_parts(parts, player, rig, names, collection, material)
    rig.location = location
    collection['mu_restoration_mode'] = 'separate_parts_shared_armature'
    collection['mu_experiment_only'] = True
    return rig, names, objects, collection


def apply_static_pose(model, rig, names, action, key):
    for index, name in enumerate(names):
        positions, rotations = bone_basis_samples(model, rig, names, index, action)
        bone = rig.pose.bones[name]
        bone.location = positions[key]
        bone.rotation_quaternion = rotations[key]
    bpy.context.view_layer.update()


def make_weapon_mesh(model, material):
    matrices = runtime_matrices(model, 0, 0)
    source = model['meshes'][0]
    vertices = [tuple(matrices[v['node'], :3, :3] @ v['position'] + matrices[v['node'], :3, 3])
                for v in source['vertices']]
    mesh = bpy.data.meshes.new('Original_Sword01_Rigid_Geometry')
    mesh.from_pydata(vertices, [], [triangle['vertices'] for triangle in source['triangles']])
    mesh.update()
    layer = mesh.uv_layers.new(name='UVMap')
    for polygon, triangle in zip(mesh.polygons, source['triangles']):
        for corner, loop in enumerate(polygon.loop_indices):
            u, v = source['uvs'][triangle['uvs'][corner]]
            layer.data[loop].uv = (u, 1.0 - v)
    mesh.materials.append(material)
    return mesh


def mount_weapon(rig, names, collection, mesh, scale):
    socket = bpy.data.objects.new(collection.name + '_Right_Weapon_Socket_33', None)
    collection.objects.link(socket)
    constraint = socket.constraints.new('COPY_TRANSFORMS')
    constraint.target = rig
    constraint.subtarget = names[SOCKET_NODE]
    constraint.target_space = 'WORLD'
    constraint.owner_space = 'WORLD'
    constraint.head_tail = 0.0
    # The normal hand-held client branch uses ParentMatrix = socket directly.
    mount = Matrix.Diagonal((scale, scale, scale, 1.0))
    weapon = bpy.data.objects.new(collection.name + '_Sword01', mesh)
    collection.objects.link(weapon)
    weapon.parent = socket
    weapon.matrix_parent_inverse = Matrix.Identity(4)
    weapon.matrix_basis = mount
    weapon['mu_source_file'] = 'Item/Sword01.bmd'
    weapon['mu_attachment_node'] = SOCKET_NODE
    weapon['mu_attachment_mode'] = ATTACHMENT_MODE
    weapon['mu_attachment_note'] = 'Player hand-held Link=false; original item pose, no added rotation or grip offset'
    return weapon, mount


def setup_preview():
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'FLAT'
    scene.display.shading.color_type = 'TEXTURE'
    scene.display.shading.show_shadows = False
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = 'BOTH'
    scene.display.shading.background_type = 'WORLD'
    scene.world = bpy.data.worlds.new('Experiment_World')
    scene.world.color = (0.085, 0.095, 0.115)
    scene.view_settings.view_transform = 'Standard'
    scene.render.resolution_x, scene.render.resolution_y = 1200, 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.fps = 24
    data = bpy.data.cameras.new('Comparison_Camera')
    camera = bpy.data.objects.new('Comparison_Camera', data)
    scene.collection.objects.link(camera)
    data.type = 'ORTHO'
    data.ortho_scale = 345.0
    camera.location = (130.0, -650.0, 235.0)
    camera.rotation_euler = (Vector((0.0, 0.0, 82.0)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.camera = camera
    return scene


def body_pose_error(player, parts, rig, objects, action, key, graph):
    expected = runtime_matrices(player, action, key)
    maximum = 0.0
    for (_, part), obj in zip(parts, objects):
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        try:
            for vertex, source in zip(mesh.vertices, part['meshes'][0]['vertices']):
                bone = expected[source['node']]
                actual = obj.matrix_world @ vertex.co
                native = bone[:3, :3] @ source['position'] + bone[:3, 3] + np.array(rig.location)
                maximum = max(maximum, float(np.max(np.abs(np.array(actual) - native))))
        finally:
            evaluated.to_mesh_clear()
    return maximum


def check_pose(player, parts, rig, objects, weapon, weapon_model, scale, action, key):
    graph = bpy.context.evaluated_depsgraph_get()
    maximum = body_pose_error(player, parts, rig, objects, action, key, graph)
    matrix = weapon.evaluated_get(graph).matrix_world
    actual = np.array([tuple(matrix @ vertex.co) for vertex in weapon.data.vertices])
    native = client_held_weapon_vertices(player, weapon_model, action, key, rig.location, scale)
    weapon_error = float(np.max(np.abs(actual - native)))
    singular_values = np.linalg.svd(np.array(matrix)[:3, :3], compute_uv=False)
    if maximum > BINDING_TOLERANCE or weapon_error > BINDING_TOLERANCE:
        raise ValueError(f'Pose mismatch {action}/{key}: body {maximum}, weapon {weapon_error}')
    if not np.allclose(singular_values, scale, atol=BINDING_TOLERANCE):
        raise ValueError('Weapon acquired nonuniform scale')
    return {'action': action, 'key': key, 'maximum_vertex_error': maximum,
            'weapon_client_vertex_error': weapon_error, 'weapon_axis_scales': singular_values.tolist()}


def rename_actions(actions):
    catalog = extract_player_actions(
        ROOT / 'src/source/Core/Globals/_enum.h',
        EXPERIMENT / 'sources/player.bmd')
    names = {record['index']: record['name'] for record in catalog['actions']}
    for action in actions:
        index = action['mu_bmd_action_index']
        action.name = f'Dwarf_{index:03}_{names[index]}'


def prepare_models(profile):
    source = parse_bmd(EXPERIMENT / 'sources/player.bmd')
    parts = [(name, parse_bmd(EXPERIMENT / 'sources' / (name + '.bmd'))) for name in PARTS]
    for _, part in parts:
        validate_part_bones(part, source)
    target = adapt_bone_positions(source, source, profile)
    target_parts = [(name, adapt_meshes(part, source, target, profile)) for name, part in parts]
    lift = ground_alignment(source, target, parts, target_parts)
    lift_root(target, lift)
    for _, part in target_parts:
        lift_root(part, lift)
    contacts = correct_contact_heights(source, target, parts, target_parts, profile)
    rotations = confirm_preserved_data(source, target)
    finite_keys = confirm_finite_animation(target, target_parts)
    print(f'Adapted {len(target["actions"])} actions / {finite_keys} poses; preserving {rotations} bone rotation keys', flush=True)
    return source, parts, target, target_parts, lift, contacts, rotations, finite_keys


def save_trial_scene(source, old_rig, old_names, rig, actions, scene, profile, output):
    select_player_action(rig, actions[4])
    apply_static_pose(source, old_rig, old_names, 4, 0)
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                space = area.spaces.active
                space.shading.color_type = 'TEXTURE'
                space.shading.light = 'FLAT'
                space.overlay.show_bones = False
                space.overlay.show_extras = False
                space.region_3d.view_location = (0.0, 0.0, 85.0)
                space.region_3d.view_distance = 390.0
                space.region_3d.view_rotation = scene.camera.rotation_euler.to_quaternion()
    scene['mu_experiment_only'] = True
    scene['mu_dwarf_profile'] = json.dumps(profile)
    scene['mu_reference_actor_note'] = 'Left actor is a static source reference; right actor has all 284 adapted actions'
    bpy.ops.wm.save_as_mainfile(filepath=str(output / 'Dwarf_Classic_Experiment.blend'))


def build(output):
    profile = json.loads((EXPERIMENT / 'profile.json').read_text(encoding='utf-8'))
    before = source_hashes()
    source, parts, target, target_parts, lift, contacts, rotations, finite_keys = prepare_models(profile)
    output.mkdir(parents=True)
    bundle = write_bundle(output, target, target_parts)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    body_material = create_skin_material(EXPERIMENT / 'skin_barbarian_01.jpg')
    old_rig, old_names, old_objects, old_collection = make_actor(source, parts, 'Original_Reference', ORIGINAL_LOCATION, body_material)
    rig, names, objects, collection = make_actor(target, target_parts, 'Dwarf_Classic_Group', DWARF_LOCATION, body_material)
    actions = create_player_actions(target, rig, names)
    rename_actions(actions)
    store_player_metadata(target, rig, names, actions, output / 'dwarf_player_metadata.json')
    weapon_model = parse_bmd(EXPERIMENT / 'sources/item/Sword01.bmd')
    validate_sword_socket(target, weapon_model)
    weapon_material = create_skin_material(EXPERIMENT / 'sword02.jpg')
    weapon_mesh = make_weapon_mesh(weapon_model, weapon_material)
    weapon, mount = mount_weapon(rig, names, collection, weapon_mesh, profile['weapon_scale'])
    old_weapon, _ = mount_weapon(old_rig, old_names, old_collection, weapon_mesh, profile['weapon_scale'])
    scene = setup_preview()
    preview_directory = output / 'previews'
    preview_directory.mkdir()
    checks = []
    for label, action, key in PREVIEW_POSES:
        select_player_action(rig, actions[action], key + 1)
        apply_static_pose(source, old_rig, old_names, action, key)
        check = check_pose(target, target_parts, rig, objects, weapon, weapon_model, profile['weapon_scale'], action, key)
        check['original_reference'] = check_pose(source, parts, old_rig, old_objects, old_weapon,
                                                  weapon_model, profile['weapon_scale'], action, key)
        checks.append(check)
        scene.render.filepath = str(preview_directory / (label + '.png'))
        bpy.ops.render.render(write_still=True)
        print(f'Rendered {label}', flush=True)
    save_trial_scene(source, old_rig, old_names, rig, actions, scene, profile, output)
    if before != source_hashes():
        raise ValueError('An original game resource changed')
    source_size = np.ptp(posed_vertices(source, parts, 4, 0), axis=0).tolist()
    target_size = np.ptp(posed_vertices(target, target_parts, 4, 0), axis=0).tolist()
    report = {'experiment_only': True, 'installed_to_game': False, 'profile': profile,
              'actions': len(actions), 'bones': len(names), 'body_parts': len(objects),
              'finite_poses_checked': finite_keys, 'bone_rotation_keys_preserved': rotations,
              'root_lift': lift, 'contact_adaptation': contacts, 'preview_checks': checks,
              'source_standing_xyz_size': source_size, 'dwarf_standing_xyz_size': target_size,
              'source_sha256_before_and_after': before, 'source_resources_unchanged': True,
              'weapon': {'source': 'Sword01.bmd', 'socket': SOCKET_NODE, 'shape_shared_with_reference': True,
                         'scale': profile['weapon_scale'], 'attachment_mode': ATTACHMENT_MODE,
                         'extra_rotation_degrees': [0.0, 0.0, 0.0], 'extra_translation': [0.0, 0.0, 0.0]},
              'generated_bundle': bundle,
              'limits': ['Class01 body only; other class and armor mappings not processed',
                         'No in-client verification; game source/data were not modified',
                         'Contact correction only for actions 4, 17, 26',
                         'Two-hand grip, mounted contact, cloth and game movement speed are not adapted',
                         'Blender key playback is 24fps, not runtime PlaySpeed',
                         'Source single-node binding limits elbow/knee shape; preview needs visual review']}
    (output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'blend': str(output / 'Dwarf_Classic_Experiment.blend'),
                      'report': str(output / 'report.json'), 'source_resources_unchanged': True}), flush=True)


if __name__ == '__main__':
    arguments = sys.argv[sys.argv.index('--') + 1:]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiment', required=True)
    parser.add_argument('--output', default='runs/v01')
    args = parser.parse_args(arguments)
    output = (EXPERIMENT / args.output).resolve()
    if not output.is_relative_to(EXPERIMENT.resolve()) or output.exists():
        raise ValueError('Choose a new directory inside this experiment')
    build(output)
