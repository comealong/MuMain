"""Continuous weighted chibi arms, modeled from the generated reference."""
import math
import bpy
import bmesh
import numpy as np

SIDES = 24
ARM_RINGS = 32


def unit(value):
    return value / np.linalg.norm(value)


def smoothstep(value):
    value = float(np.clip(value, 0.0, 1.0))
    return value * value * (3.0 - 2.0 * value)


class Surface:
    def __init__(self):
        self.vertices, self.faces, self.weights, self.materials = [], [], [], []

    def sweep(self, centers, radii, weights, materials, depth=0.9):
        offset = len(self.vertices)
        for index, (center, radius, binding) in enumerate(zip(centers, radii, weights)):
            before, after = centers[max(0, index - 1)], centers[min(len(centers) - 1, index + 1)]
            tangent = unit(after - before)
            side = unit(np.cross(tangent, (0.0, 1.0, 0.0)))
            front = unit(np.cross(side, tangent))
            for step in range(SIDES):
                angle = math.tau * step / SIDES
                self.vertices.append(tuple(center + radius * (math.cos(angle) * side + depth * math.sin(angle) * front)))
                self.weights.append(binding)
        for ring in range(len(centers) - 1):
            for side in range(SIDES):
                a = offset + ring * SIDES + side
                b = offset + ring * SIDES + (side + 1) % SIDES
                self.faces.append((a, b, b + SIDES, a + SIDES))
                self.materials.append(materials[ring])
        for ring, reverse in ((0, True), (len(centers) - 1, False)):
            face = [offset + ring * SIDES + side for side in range(SIDES)]
            self.faces.append(tuple(reversed(face)) if reverse else tuple(face))
            self.materials.append(materials[ring])

    def ellipsoid(self, center, axes, radii, bone, material):
        rings = 14
        centers, widths = [], []
        for ring in range(rings + 1):
            theta = math.pi * ring / rings
            centers.append(center + axes[0] * radii[0] * math.cos(theta))
            widths.append(max(0.015, radii[1] * math.sin(theta)))
        # sweep is rotational around its axis; the depth factor makes a mitten palm.
        self.sweep(centers, widths, [{bone: 1.0}] * len(centers),
                   [material] * len(centers), radii[2] / radii[1])


def arm_path(shoulder, elbow, wrist, upper, forearm, hand):
    start = shoulder.copy()
    start[0] -= math.copysign(6.0, shoulder[0])
    start[2] += 1.0
    centers, radii, bindings, materials = [], [], [], []
    for ring in range(ARM_RINGS + 1):
        t = ring / ARM_RINGS
        # The elbow remains a real joint, with a continuous surface across it.
        if t <= 0.55:
            u = t / 0.55
            center = start * (1.0 - u) + elbow * u
        else:
            u = (t - 0.55) / 0.45
            center = elbow * (1.0 - u) + wrist * u
        radius = float(np.interp(t, [0, 0.10, 0.28, 0.55, 0.70, 1.0],
                                  [3.0, 6.4, 6.2, 5.4, 5.8, 4.0]))
        blend = smoothstep((t - 0.41) / 0.28)
        centers.append(center)
        radii.append(radius)
        wrist_blend = smoothstep((t - 0.82) / 0.18)
        bindings.append({upper: (1.0 - blend) * (1.0 - wrist_blend),
                         forearm: blend * (1.0 - wrist_blend), hand: wrist_blend})
        materials.append(0 if t < 0.52 else 1)
    return centers, radii, bindings, materials


def add_cuff(surface, elbow, wrist, forearm):
    direction = unit(wrist - elbow)
    centers = [elbow + direction * value for value in (-0.3, 0.3, 1.2, 2.2, 2.8)]
    radii = [5.4, 6.9, 7.1, 6.6, 5.7]
    surface.sweep(centers, radii, [{forearm: 1.0}] * len(centers), [2] * len(centers))


def add_hand(surface, wrist, socket, hand):
    direction = unit(socket - wrist)
    side = unit(np.cross(direction, (0.0, 1.0, 0.0)))
    front = unit(np.cross(side, direction))
    center = (wrist + socket) * 0.5 + direction * 0.5
    axes = (direction, side, front)
    surface.ellipsoid(center, axes, (5.0, 5.0, 4.3), hand, 1)
    # A thumb distinguishes the glove from a ball, while remaining compact.
    thumb = center + side * 3.4 - direction * 0.7 - np.array((0.0, 1.4, 0.0))
    surface.ellipsoid(thumb, axes, (2.8, 2.4, 2.2), hand, 1)


def replace_arms(obj, rig, names, skin, glove, cuff):
    point = lambda node: np.array(rig.data.bones[names[node]].matrix_local.translation)
    surface = Surface()
    for upper, forearm, hand, socket in ((26, 27, 28, 33), (35, 36, 37, 42)):
        shoulder, elbow, wrist = point(upper), point(forearm), point(hand)
        surface.sweep(*arm_path(shoulder, elbow, wrist, upper, forearm, hand))
        add_cuff(surface, elbow, wrist, forearm)
        add_hand(surface, wrist, point(socket), hand)
    mesh = bpy.data.meshes.new('Chibi_Continuous_Arms')
    mesh.from_pydata(surface.vertices, [], surface.faces)
    mesh.update()
    for material in (skin, glove, cuff):
        mesh.materials.append(material)
    for face, index in zip(mesh.polygons, surface.materials):
        face.material_index = index
        face.use_smooth = True
    editable = bmesh.new()
    editable.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(editable, faces=list(editable.faces))
    editable.to_mesh(mesh)
    editable.free()
    obj.data = mesh
    obj.vertex_groups.clear()
    groups = {node: obj.vertex_groups.new(name=names[node]) for node in (26, 27, 28, 35, 36, 37)}
    for index, binding in enumerate(surface.weights):
        for node, weight in binding.items():
            if weight > 0.0:
                groups[node].add([index], weight, 'REPLACE')
    obj['mu_arm_revision'] = 'Continuous shoulder-elbow-wrist surface; blended elbow weights; no clavicle capsules'
    obj['mu_reference'] = 'references/Chibi_Concept.png'
