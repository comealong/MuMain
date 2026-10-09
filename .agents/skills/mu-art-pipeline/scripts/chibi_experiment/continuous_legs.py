"""Continuous knee and ankle envelopes for the saved Class01 chibi experiment."""
import bpy
import numpy as np
from surface import unit, smoothstep

LEGS = ((3, 4, 5, 6), (10, 11, 12, 13))
RING_COUNT = 97
PATH_END = 3.0
HIP_EXTENSION = np.array((0., 0., 3.))
HIP_VOLUME_OFFSET = np.array((0., 0., 2.))
HIP_RADII = (8., 20., 12.)
FOOT_CENTER_HEIGHT = 7.0
FOOT_RADII = (6.8, 8.8, 14.0)
UP = np.array((0., 0., 1.))
RADIUS_TIMES = (0., .2, .70, 1., 1.12, 1.35, 1.75, 2., 2.6, 3.)
RADII = (8.5, 9.2, 8.9, 8.1, 8.3, 7.85, 7.3, 7.0, 7.3, 7.6)
SECTION_DEPTH = 1.0
CUFF_START = .98
CUFF_END = 1.16
KNEE_BLEND_START = .68
KNEE_BLEND_LENGTH = .64
ANKLE_BLEND_START = 1.60
ANKLE_BLEND_LENGTH = .80
ANKLE_RELAX_RADIUS = 13.0
ANKLE_RELAX_HEIGHT = 10.0
ANKLE_RELAX_ITERATIONS = 22
ANKLE_RELAX_FACTOR = .45


def joint_binding(value, thigh, calf, foot):
    knee = smoothstep((value - KNEE_BLEND_START) / KNEE_BLEND_LENGTH)
    ankle = smoothstep((value - ANKLE_BLEND_START) / ANKLE_BLEND_LENGTH)
    return {thigh: 1. - knee, calf: knee * (1. - ankle), foot: knee * ankle}


def surface_role(value):
    if value < CUFF_START:
        return 4
    return 6 if value < CUFF_END else 5


def continuous_leg(surface, point, nodes):
    from connected_body import catmull_point
    thigh, calf, foot, toe = nodes
    hip, knee, ankle, tip = (point(node) for node in nodes)
    foot_center = (ankle + tip) * .5
    foot_center[2] = max(foot_center[2], FOOT_CENTER_HEIGHT)
    controls = (hip + HIP_EXTENSION, knee, ankle, foot_center)
    centers, radii, weights, roles = [], [], [], []
    for value in np.linspace(0., PATH_END, RING_COUNT):
        segment = min(int(value), len(controls) - 2)
        centers.append(catmull_point(controls, segment, value - segment))
        radii.append(float(np.interp(value, RADIUS_TIMES, RADII)))
        weights.append(joint_binding(value, thigh, calf, foot))
        roles.append(surface_role(value))
    # There are no caps at either the knee or ankle: both are interior rings.
    surface.sweep(centers, radii, weights, roles, depth=SECTION_DEPTH)
    surface.ellipsoid(foot_center, (UP,), FOOT_RADII, foot, 5)


def lower_body(surface, point):
    surface.ellipsoid(point(2) - HIP_VOLUME_OFFSET, (UP,), HIP_RADII, 2, 4)
    for nodes in LEGS:
        continuous_leg(surface, point, nodes)


def soften_ankle_envelopes(obj, point):
    """Soften the instep union while preserving the toe, sole and knee trim."""
    group_name = 'Ankle_Instep_Transition'
    group = obj.vertex_groups.new(name=group_name)
    for vertex in obj.data.vertices:
        position = np.array(vertex.co)
        ankle = point(5 if position[0] > 0 else 12)
        height = abs(position[2] - ankle[2]) / ANKLE_RELAX_HEIGHT
        distance = np.linalg.norm(position - ankle) / ANKLE_RELAX_RADIUS
        amount = (1. - smoothstep(height)) * (1. - smoothstep(distance))
        if amount > 0.:
            group.add([vertex.index], amount, 'REPLACE')
    modifier = obj.modifiers.new('Smooth Boot Instep', 'SMOOTH')
    modifier.vertex_group = group_name
    modifier.factor = ANKLE_RELAX_FACTOR
    modifier.iterations = ANKLE_RELAX_ITERATIONS
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    current = obj.vertex_groups.get(group_name)
    if current is not None:
        obj.vertex_groups.remove(current)
