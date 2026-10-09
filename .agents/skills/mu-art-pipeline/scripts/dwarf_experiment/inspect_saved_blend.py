"""Reopen the saved trial and compare sword vertices with the client held-item path."""
from pathlib import Path
import json
import sys

import bpy
import numpy as np

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import workspace_path
from mu_art_pipeline.bmd import parse_bmd
from weapon_attachment import (
    ATTACHMENT_MODE, RIGHT_WEAPON_NODE, validate_sword_socket, client_held_weapon_vertices,
)

VALIDATION_ACTION = 39
VERTEX_TOLERANCE = 0.001
SCALE_TOLERANCE = 0.00001


def require(condition, message):
    if not condition:
        raise ValueError(message)


def inspect_structure(report, rig, weapon):
    parts = [obj for obj in bpy.data.collections['Dwarf_Classic_Group'].objects
             if obj.type == 'MESH' and obj != weapon]
    actions = {action['mu_bmd_action_index']: action for action in bpy.data.actions
               if 'mu_bmd_action_index' in action}
    require(len(parts) == report['body_parts'], 'Body part count changed')
    require(len(rig.data.bones) == report['bones'], 'Bone count changed')
    require(len(actions) == report['actions'], 'Action count changed')
    require(all(len(obj.modifiers) == 1 and obj.modifiers[0].object == rig for obj in parts),
            'Body meshes must share one armature')
    require(all(image.packed_file is not None for image in bpy.data.images if image.source == 'FILE'),
            'A texture is not packed')
    require(weapon.data == bpy.data.objects['Original_Reference_Sword01'].data,
            'Weapon mesh must match the reference')
    require(weapon.get('mu_attachment_mode') == ATTACHMENT_MODE, 'Incorrect attachment branch')
    constraint = weapon.parent.constraints[0]
    socket_bone = rig.data.bones.get(constraint.subtarget)
    require(constraint.target == rig and socket_bone is not None
            and socket_bone.get('mu_bmd_node') == RIGHT_WEAPON_NODE, 'Incorrect weapon socket')
    return parts, actions


def inspect_attack(output, rig, weapon, action, scale):
    player = parse_bmd(output / 'generated/Player/player.bmd')
    sword = parse_bmd(output / 'generated/Item/Sword01.bmd')
    validate_sword_socket(player, sword)
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    axis_errors, vertex_errors = [], []
    for key in range(action['mu_bmd_keys']):
        bpy.context.scene.frame_set(key + 1)
        graph = bpy.context.evaluated_depsgraph_get()
        matrix = weapon.evaluated_get(graph).matrix_world
        scales = np.linalg.svd(np.array(matrix)[:3, :3], compute_uv=False)
        axis_errors.append(float(np.max(np.abs(scales - scale))))
        actual = np.array([tuple(matrix @ vertex.co) for vertex in weapon.data.vertices])
        native = client_held_weapon_vertices(player, sword, VALIDATION_ACTION, key, rig.location, scale)
        vertex_errors.append(float(np.max(np.abs(actual - native))))
    require(max(axis_errors) < SCALE_TOLERANCE, 'Weapon acquired nonuniform scale')
    require(max(vertex_errors) < VERTEX_TOLERANCE, 'Weapon differs from the client held-item path')
    return max(axis_errors), max(vertex_errors)


def main():
    output = workspace_path(Path(bpy.data.filepath).parent)
    report = json.loads((output / 'report.json').read_text(encoding='utf-8'))
    rig = bpy.data.objects['Dwarf_Classic_Group_Armature']
    weapon = bpy.data.objects['Dwarf_Classic_Group_Sword01']
    parts, actions = inspect_structure(report, rig, weapon)
    axis_error, vertex_error = inspect_attack(output, rig, weapon, actions[VALIDATION_ACTION],
                                             report['profile']['weapon_scale'])
    result = {'passed': True, 'reopened_blend': bpy.data.filepath, 'dwarf_body_parts': len(parts),
              'bones': len(rig.data.bones), 'actions': len(actions), 'textures_packed': True,
              'weapon_shares_original_mesh': True, 'weapon_attachment_mode': ATTACHMENT_MODE,
              'attack_39_weapon_maximum_scale_error': axis_error,
              'attack_39_weapon_client_vertex_error': vertex_error}
    (output / 'blend_validation.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
