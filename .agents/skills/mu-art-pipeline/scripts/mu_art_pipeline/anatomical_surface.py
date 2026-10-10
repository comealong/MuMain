"""Anatomical surface primitives with caller-supplied paths, axes and sizes."""
from __future__ import annotations

import numpy as np

DIRECTION_TOLERANCE = 64 * np.finfo(float).eps
ORTHOGONALITY_TOLERANCE = 1e-6
MIN_POLYGON_SIDES = 3


def vectors(values, name, minimum_count):
    result = np.asarray(values, dtype=float)
    if result.ndim != 2 or result.shape[1] != 3 or len(result) < minimum_count:
        raise ValueError(f'{name} must be an array of three-dimensional points')
    if not np.isfinite(result).all():
        raise ValueError(f'{name} must be finite')
    return result


def unit(vector):
    length = float(np.linalg.norm(vector))
    if not np.isfinite(length) or length == 0:
        raise ValueError('A direction cannot be zero or nonfinite')
    return vector / length


def section_axis(tangent):
    candidate = np.eye(3)[int(np.argmin(np.abs(tangent)))]
    return unit(candidate - tangent * np.dot(candidate, tangent))


def transported_frames(centers, reference_axis):
    differences = np.diff(centers, axis=0)
    if (np.linalg.norm(differences, axis=1) == 0).any():
        raise ValueError('Consecutive path centers must be distinct')
    tangents = [unit(differences[0])]
    tangents.extend(unit(centers[i + 1] - centers[i - 1]) for i in range(1, len(centers) - 1))
    tangents.append(unit(differences[-1]))
    tangent = tangents[0]
    normal = section_axis(tangent) if reference_axis is None else unit(np.asarray(reference_axis, dtype=float))
    normal = unit(normal - tangent * np.dot(normal, tangent))
    frames = []
    previous = tangent
    for tangent in tangents:
        turn = np.cross(previous, tangent)
        sine = float(np.linalg.norm(turn))
        cosine = float(np.clip(np.dot(previous, tangent), -1, 1))
        if sine > DIRECTION_TOLERANCE:
            axis = turn / sine
            normal = (normal * cosine + np.cross(axis, normal) * sine
                      + axis * np.dot(axis, normal) * (1 - cosine))
        elif cosine < 0:
            raise ValueError('A reversing path needs an explicit joint/cusp treatment')
        normal = unit(normal - tangent * np.dot(normal, tangent))
        frames.append((normal.copy(), np.cross(tangent, normal)))
        previous = tangent
    return np.asarray(frames)


def sweep_radii(radii, count):
    radii = np.asarray(radii, dtype=float)
    if radii.shape == (count,):
        radii = np.column_stack((radii, radii))
    if radii.shape != (count, 2) or not np.isfinite(radii).all() or (radii <= 0).any():
        raise ValueError('Supply positive circular or two-axis radii for each center')
    return radii


def sweep_faces(count, sides, cap_ends):
    faces = []
    for ring in range(count - 1):
        for side in range(sides):
            following = (side + 1) % sides
            faces.append((ring * sides + side, ring * sides + following,
                          (ring + 1) * sides + following, (ring + 1) * sides + side))
    if cap_ends:
        faces.append(tuple(reversed(range(sides))))
        faces.append(tuple((count - 1) * sides + side for side in range(sides)))
    return faces


def sweep_surface(centers, radii, *, sides, cap_ends=True, reference_axis=None):
    centers = vectors(centers, 'Centers', 2)
    if not isinstance(sides, int) or sides < MIN_POLYGON_SIDES:
        raise ValueError('Section sides must be an integer of at least three')
    radii = sweep_radii(radii, len(centers))
    frames = transported_frames(centers, reference_axis)
    angles = np.arange(sides) * np.pi * 2 / sides
    offsets = (frames[:, None, 0] * (radii[:, 0, None] * np.cos(angles))[..., None]
               + frames[:, None, 1] * (radii[:, 1, None] * np.sin(angles))[..., None])
    vertices = (centers[:, None] + offsets).reshape(-1, 3)
    return {'vertices':vertices, 'faces':sweep_faces(len(centers), sides, cap_ends),
            'ring_index':np.repeat(np.arange(len(centers)), sides)}


def catmull_rom_points(control_points, *, samples_per_segment):
    points = vectors(control_points, 'Control points', 2)
    if not isinstance(samples_per_segment, int) or samples_per_segment <= 0:
        raise ValueError('Samples per segment must be a positive integer')
    result = []
    for segment in range(len(points) - 1):
        p0 = points[max(segment - 1, 0)]
        p1, p2 = points[segment], points[segment + 1]
        p3 = points[min(segment + 2, len(points) - 1)]
        for sample in range(samples_per_segment):
            t = sample / samples_per_segment
            result.append(.5 * ((2 * p1) + (-p0 + p2) * t
                + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t))
    return np.asarray(result + [points[-1]])


def ellipsoid_faces(latitude_segments, sides):
    faces = [(0, 1 + side, 1 + (side + 1) % sides) for side in range(sides)]
    for ring in range(latitude_segments - 2):
        start = 1 + ring * sides
        for side in range(sides):
            following = (side + 1) % sides
            faces.append((start + side, start + sides + side,
                          start + sides + following, start + following))
    last = 1 + (latitude_segments - 2) * sides
    pole = 1 + (latitude_segments - 1) * sides
    faces.extend((last + side, pole, last + (side + 1) % sides) for side in range(sides))
    return faces


def ellipsoid_surface(center, axes, radii, *, latitude_segments, sides):
    center = np.asarray(center, dtype=float)
    axes = np.asarray(axes, dtype=float)
    radii = np.asarray(radii, dtype=float)
    if center.shape != (3,) or radii.shape != (3,) or axes.shape != (3, 3):
        raise ValueError('Center/radii need three values and axes need three row vectors')
    if not all(np.isfinite(value).all() for value in (center, axes, radii)) or (radii <= 0).any():
        raise ValueError('Ellipsoid parameters must be finite, with positive radii')
    if not np.allclose(axes @ axes.T, np.eye(3), atol=ORTHOGONALITY_TOLERANCE, rtol=0):
        raise ValueError('Ellipsoid axes must be orthonormal')
    if not isinstance(latitude_segments, int) or latitude_segments < 2:
        raise ValueError('Latitude segments must be an integer of at least two')
    if not isinstance(sides, int) or sides < MIN_POLYGON_SIDES:
        raise ValueError('Longitude sides must be an integer of at least three')
    theta = np.arange(1, latitude_segments) * np.pi / latitude_segments
    phi = np.arange(sides) * np.pi * 2 / sides
    local = np.empty((len(theta), sides, 3))
    local[..., 0] = radii[0] * np.cos(theta)[:, None]
    local[..., 1] = radii[1] * np.sin(theta)[:, None] * np.cos(phi)
    local[..., 2] = radii[2] * np.sin(theta)[:, None] * np.sin(phi)
    body = center + local.reshape(-1, 3) @ axes
    poles = center + np.array(((radii[0], 0, 0), (-radii[0], 0, 0))) @ axes
    vertices = np.vstack((poles[0], body, poles[1]))
    faces = ellipsoid_faces(latitude_segments, sides)
    if np.linalg.det(axes) < 0:
        faces = [tuple(reversed(face)) for face in faces]
    return {'vertices':vertices, 'faces':faces}
