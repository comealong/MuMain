"""Experimental proportion adaptation; source rotations and vertex node IDs are preserved."""
from copy import deepcopy

import numpy as np
from mu_art_pipeline.poses import pose_matrices

REFERENCE_ACTION = 0
REFERENCE_KEY = 0
STANDING_ACTION = 4
ROOT_NODE = 0
HEAD_SEGMENT_LENGTH = 18.0
FALLBACK_SEGMENT_LENGTH = 8.0
NORMAL_DIFFERENCE_STEP = 0.01


def shape_scale(name, profile):
    """Biped local X follows segment length; Y/Z span its cross section."""
    if name == 'Bip01 Pelvis' or 'Spine' in name or name.startswith('Bone'):
        return (profile['torso_length'], profile['body_depth'], profile['body_width'])
    if 'Thigh' in name or 'Calf' in name:
        return (profile['leg_length'], profile['limb_thickness'], profile['limb_thickness'])
    if 'Clavicle' in name:
        return (profile['body_width'], profile['body_depth'], profile['body_width'])
    if 'UpperArm' in name or 'Forearm' in name:
        return (profile['arm_length'], profile['limb_thickness'], profile['limb_thickness'])
    if name == 'Bip01 Neck':
        return (profile['neck_length'], profile['head_size'], profile['head_size'])
    if name == 'Bip01 Head' or 'Ponytail' in name:
        return (profile['head_size'],) * 3
    if 'Hand' in name or 'Finger' in name:
        return (profile['hand_size'],) * 3
    if 'Foot' in name or 'Toe' in name:
        return (profile['foot_size'],) * 3
    return (1.0, 1.0, 1.0)


def adapt_bone_positions(model, player, profile, root_lift=0.0):
    result = deepcopy(model)
    for index, bone in enumerate(result['bones']):
        if bone['dummy']:
            continue
        parent = bone['parent']
        parent_scale = np.array(shape_scale(player['bones'][parent]['name'], profile)) if parent >= 0 else None
        for action in bone['actions']:
            values = np.array(action['positions'], dtype=float)
            if parent < 0:
                values *= (profile['stride_scale'], profile['stride_scale'], profile['leg_length'])
                values[:, 2] += root_lift
            else:
                values *= parent_scale
            action['positions'] = values.tolist()
    for action in result['actions']:
        if action['lock_positions']:
            values = np.array(action['positions'], dtype=float)
            values *= (profile['stride_scale'], profile['stride_scale'], profile['leg_length'])
            values[:, 2] += root_lift
            action['positions'] = values.tolist()
    return result


def deformation_handles(source, target, profile):
    source_rest = np.array(pose_matrices(source, REFERENCE_ACTION, REFERENCE_KEY))
    target_rest = np.array(pose_matrices(target, REFERENCE_ACTION, REFERENCE_KEY))
    handles = []
    for index, bone in enumerate(source['bones']):
        name = bone['name']
        if bone['dummy'] or not name.startswith('Bip01 ') or 'Footsteps' in name or 'Ponytail' in name:
            continue
        child = next((j for j, b in enumerate(source['bones']) if b['parent'] == index
                      and b['name'].startswith('Bip01 ') and 'Ponytail' not in b['name']), None)
        start = source_rest[index, :3, 3]
        fallback = HEAD_SEGMENT_LENGTH if name == 'Bip01 Head' else FALLBACK_SEGMENT_LENGTH
        end = source_rest[child, :3, 3] if child is not None else start + source_rest[index, :3, 0] * fallback
        scale = np.eye(4)
        scale[:3, :3] = np.diag(shape_scale(name, profile))
        mapping = target_rest[index] @ scale @ np.linalg.inv(source_rest[index])
        handles.append((start, end, mapping))
    return source_rest, target_rest, handles


def warp_position(position, handles, radius):
    point = np.array(position, dtype=float)
    transformed, weights = [], []
    for start, end, mapping in handles:
        segment = end - start
        squared_length = float(segment @ segment)
        factor = float(np.clip((point - start) @ segment / squared_length, 0.0, 1.0)) if squared_length else 0.0
        delta = point - (start + factor * segment)
        weights.append(1.0 / (radius * radius + float(delta @ delta)) ** 2)
        transformed.append(mapping[:3, :3] @ point + mapping[:3, 3])
    weights = np.array(weights)
    return np.average(transformed, weights=weights, axis=0)


def warp_normal(position, normal, handles, radius):
    step = NORMAL_DIFFERENCE_STEP
    jacobian = np.column_stack([
        (warp_position(position + np.eye(3)[axis] * step, handles, radius)
         - warp_position(position - np.eye(3)[axis] * step, handles, radius)) / (2 * step)
        for axis in range(3)])
    result = np.linalg.solve(jacobian.T, normal)
    length = np.linalg.norm(result)
    return result / length if length else result


def adapt_meshes(part, source, target, profile):
    result = adapt_bone_positions(part, source, profile)
    source_rest, target_rest, handles = deformation_handles(source, target, profile)
    inverses = np.linalg.inv(target_rest)
    radius = profile['skin_blend_radius']
    for mesh in result['meshes']:
        old_vertices = deepcopy(mesh['vertices'])
        for vertex in mesh['vertices']:
            node = vertex['node']
            world = source_rest[node, :3, :3] @ vertex['position'] + source_rest[node, :3, 3]
            warped = warp_position(world, handles, radius)
            vertex['position'] = (inverses[node, :3, :3] @ warped + inverses[node, :3, 3]).tolist()
        for normal in mesh['normals']:
            node = normal['node']
            bound = normal['bind_vertex']
            vertex = old_vertices[bound] if 0 <= bound < len(old_vertices) else old_vertices[0]
            world = source_rest[vertex['node'], :3, :3] @ vertex['position'] + source_rest[vertex['node'], :3, 3]
            direction = source_rest[node, :3, :3] @ normal['normal']
            warped = warp_normal(world, direction, handles, radius)
            normal['normal'] = (inverses[node, :3, :3] @ warped).tolist()
    return result


def posed_vertices(model, parts, action, key):
    matrices = np.array(pose_matrices(model, action, key))
    output = []
    for _, part in parts:
        for mesh in part['meshes']:
            for vertex in mesh['vertices']:
                matrix = matrices[vertex['node']]
                output.append(matrix[:3, :3] @ vertex['position'] + matrix[:3, 3])
    return np.array(output)


def ground_alignment(source, target, source_parts, target_parts):
    source_low = posed_vertices(source, source_parts, STANDING_ACTION, 0)[:, 2].min()
    target_low = posed_vertices(target, target_parts, STANDING_ACTION, 0)[:, 2].min()
    return float(source_low - target_low)


def lift_root(model, offset):
    for bone in model['bones']:
        if bone['dummy'] or bone['parent'] >= 0:
            continue
        for action in bone['actions']:
            for position in action['positions']:
                position[2] += offset
    for action in model['actions']:
        for position in action['positions']:
            position[2] += offset


def confirm_preserved_data(source, target):
    if len(source['actions']) != len(target['actions']) or len(source['bones']) != len(target['bones']):
        raise ValueError('Skeleton/action count changed')
    rotation_keys = 0
    for old, new in zip(source['bones'], target['bones']):
        for field in ('name', 'parent', 'dummy'):
            if old[field] != new[field]:
                raise ValueError('Bone mapping changed')
        for old_action, new_action in zip(old['actions'], new['actions']):
            if old_action['rotations'] != new_action['rotations']:
                raise ValueError('Rotation key changed')
            rotation_keys += len(old_action['rotations'])
    for old, new in zip(source['actions'], target['actions']):
        if (old['keys'], old['lock_positions']) != (new['keys'], new['lock_positions']):
            raise ValueError('Action layout changed')
    return rotation_keys


def confirm_finite_animation(model, parts):
    total_keys = 0
    for action_index, action in enumerate(model['actions']):
        for key in range(action['keys']):
            points = posed_vertices(model, parts, action_index, key)
            if not np.isfinite(points).all():
                raise ValueError(f'Non-finite pose {action_index}/{key}')
            total_keys += 1
    return total_keys
