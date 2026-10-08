"""Create one Blender armature and layered actions from a MU Player skeleton."""
from __future__ import annotations

import json
import bpy
from mathutils import Matrix

from .poses import IDENTITY, local_matrix, pose_matrices

BONE_DISPLAY_LENGTH = 3.0


def create_shared_armature(player: dict, collection, name: str):
    data = bpy.data.armatures.new(name)
    rig = bpy.data.objects.new(name, data)
    collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    rest = pose_matrices(player, 0, 0)
    bones = []
    for index, record in enumerate(player['bones']):
        bone = data.edit_bones.new(record['name'])
        bone.matrix = Matrix(rest[index])
        bone.length = BONE_DISPLAY_LENGTH
        bone.use_deform = not record['dummy']
        bones.append(bone)
    for index, record in enumerate(player['bones']):
        if record['parent'] >= 0:
            bones[index].parent = bones[record['parent']]
    names = [bone.name for bone in bones]
    bpy.ops.object.mode_set(mode='OBJECT')
    for index, name in enumerate(names):
        data.bones[name]['mu_bmd_node'] = index
        rig.pose.bones[name].rotation_mode = 'QUATERNION'
    rig.show_in_front = True
    data.display_type = 'STICK'
    rig.animation_data_create()
    return rig, names


def bone_basis_samples(player: dict, rig, names: list[str], index: int, action_index: int):
    record = player['bones'][index]
    bone = rig.data.bones[names[index]]
    parent_rest = bone.parent.matrix_local if bone.parent else Matrix.Identity(4)
    correction = bone.matrix_local.inverted() @ parent_rest
    action = record['actions'][action_index] if not record['dummy'] else None
    count = player['actions'][action_index]['keys']
    previous_rotation = None
    locations, rotations = [], []
    for key in range(count):
        local = Matrix(IDENTITY)
        if action:
            position = list(action['positions'][key])
            if index == 0 and player['actions'][action_index]['lock_positions']:
                position[:2] = action['positions'][0][:2]
            local = Matrix(local_matrix(position, action['rotations'][key]))
        basis = correction @ local
        rotation = basis.to_quaternion()
        if previous_rotation is not None and previous_rotation.dot(rotation) < 0:
            rotation.negate()
        previous_rotation = rotation.copy()
        locations.append(tuple(basis.translation))
        rotations.append(tuple(rotation))
    return locations, rotations


def write_channels(curves, path: str, samples: list, width: int):
    for axis in range(width):
        curve = curves.new(path, index=axis)
        curve.keyframe_points.add(len(samples))
        coordinates = [value for key, sample in enumerate(samples, 1) for value in (key, sample[axis])]
        curve.keyframe_points.foreach_set('co', coordinates)
        for point in curve.keyframe_points:
            point.interpolation = 'LINEAR'
        curve.update()


def create_player_actions(player: dict, rig, names: list[str]) -> list:
    actions = []
    for action_index, record in enumerate(player['actions']):
        label = 'PLAYER_STOP_MALE' if action_index == 1 else f'Action_{action_index:03}'
        action = bpy.data.actions.new(f'Player_{action_index:03}_{label}')
        action.use_fake_user = True
        action['mu_bmd_action_index'] = action_index
        action['mu_bmd_keys'] = record['keys']
        action['mu_bmd_lock_positions'] = record['lock_positions']
        slot = action.slots.new(id_type='OBJECT', name=rig.name)
        strip = action.layers.new('Player Bones').strips.new(type='KEYFRAME')
        curves = strip.channelbag(slot, ensure=True).fcurves
        for index, name in enumerate(names):
            locations, rotations = bone_basis_samples(player, rig, names, index, action_index)
            path = rig.pose.bones[name].path_from_id()
            write_channels(curves, path + '.location', locations, 3)
            write_channels(curves, path + '.rotation_quaternion', rotations, 4)
        actions.append(action)
        if action_index % 40 == 0:
            print(f'Created Player action {action_index}/{len(player["actions"])}', flush=True)
    return actions


def select_player_action(rig, action, frame: int = 1):
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = max(action['mu_bmd_keys'], 1)
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()


def store_player_metadata(player: dict, rig, names: list[str], actions: list, destination):
    metadata = {'name': player['name'], 'bones': player['bones'], 'actions': player['actions'],
                'blender_bone_names': names, 'blender_action_names': [a.name for a in actions],
                'rest_matrices': [[list(row) for row in rig.data.bones[name].matrix_local] for name in names]}
    # Text.write inserts a large single line character by character; file loading avoids that cost.
    destination.write_text(json.dumps(metadata, separators=(',', ':')), encoding='utf-8')
    text = bpy.data.texts.load(str(destination))
    text.name = 'Player_BMD_Source'
    rig['mu_bmd_source_text'] = text.name
    rig['mu_bmd_action_count'] = len(actions)
    rig['mu_bmd_source'] = player['name']
