"""Read/write shared Blender surface bindings without scene or bone presets."""
from __future__ import annotations

import numpy as np

SOURCE_ATTRIBUTE = 'mu_connected_source_vertex'
WEIGHT_SUM_TOLERANCE = 1e-5


def source_ids(obj, attribute=SOURCE_ATTRIBUTE):
    if obj.type != 'MESH':
        raise ValueError('Shared bindings require mesh objects')
    layer = obj.data.attributes.get(attribute)
    if layer is None or layer.domain != 'POINT' or layer.data_type != 'INT':
        raise ValueError(f'Missing integer point identity attribute: {attribute}')
    values = np.empty(len(obj.data.vertices), dtype=np.int32)
    layer.data.foreach_get('value', values)
    if (values < 0).any():
        raise ValueError('Shared identities must be assigned nonnegative values')
    return values


def mesh_coordinates(mesh, transform):
    values = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get('co', values)
    coordinates = values.reshape(-1, 3).astype(float)
    matrix = np.asarray(transform, dtype=float)
    if matrix.shape != (4, 4) or not np.isfinite(matrix).all():
        raise ValueError('The coordinate transform must be a finite four-by-four matrix')
    return coordinates @ matrix[:3, :3].T + matrix[:3, 3]


def vertex_weights(obj, group_names):
    columns = {name:index for index, name in enumerate(group_names)}
    groups = {group.index:columns[group.name] for group in obj.vertex_groups if group.name in columns}
    weights = np.zeros((len(obj.data.vertices), len(group_names)))
    for vertex in obj.data.vertices:
        for group in vertex.groups:
            if group.group in groups:
                weights[vertex.index, groups[group.group]] = group.weight
    return weights


def require_group_names(group_names):
    names = tuple(group_names)
    if not names or any(not isinstance(name, str) or not name for name in names):
        raise ValueError('Provide nonempty binding group names')
    if len(set(names)) != len(names):
        raise ValueError('Binding group names must be unique')
    return names


def merge_rows(ids, incoming_coordinates, incoming_weights, coordinates, weights,
               seen, position_tolerance, weight_tolerance):
    for row, index in enumerate(ids):
        if seen[index]:
            position_error = np.linalg.norm(coordinates[index] - incoming_coordinates[row])
            weight_error = np.max(np.abs(weights[index] - incoming_weights[row]))
            if position_error > position_tolerance or weight_error > weight_tolerance:
                raise ValueError('Shared identities have inconsistent positions or bindings')
        else:
            coordinates[index] = incoming_coordinates[row]
            weights[index] = incoming_weights[row]
            seen[index] = True


def shared_edges(objects, identities, attribute):
    result = []
    for obj in objects:
        ids = np.searchsorted(identities, source_ids(obj, attribute))
        values = np.empty(len(obj.data.edges) * 2, dtype=np.int32)
        obj.data.edges.foreach_get('vertices', values)
        result.append(ids[values.reshape(-1, 2)])
    return np.unique(np.sort(np.concatenate(result), axis=1), axis=0)


def read_shared_surface(objects, group_names, *, space_matrix,
                        position_tolerance, weight_tolerance, attribute=SOURCE_ATTRIBUTE):
    objects = tuple(objects)
    names = require_group_names(group_names)
    if not objects:
        raise ValueError('Provide the surface mesh objects')
    if not all(np.isfinite(t) and t >= 0 for t in (position_tolerance, weight_tolerance)):
        raise ValueError('Correspondence tolerances must be finite and nonnegative')
    identities = np.unique(np.concatenate([source_ids(obj, attribute) for obj in objects]))
    if not len(identities):
        raise ValueError('The shared surface has no vertices')
    coordinates = np.zeros((len(identities), 3))
    weights = np.zeros((len(identities), len(names)))
    seen = np.zeros(len(identities), dtype=bool)
    inverse_space = space_matrix.inverted()
    for obj in objects:
        ids = np.searchsorted(identities, source_ids(obj, attribute))
        positions = mesh_coordinates(obj.data, inverse_space @ obj.matrix_world)
        bindings = vertex_weights(obj, names)
        merge_rows(ids, positions, bindings, coordinates, weights, seen,
                   position_tolerance, weight_tolerance)
    if not np.isfinite(coordinates).all() or not np.isfinite(weights).all():
        raise ValueError('Shared positions and bindings must be finite')
    if not np.allclose(weights.sum(axis=1), 1, atol=WEIGHT_SUM_TOLERANCE, rtol=0):
        raise ValueError('Selected groups must include the complete normalized bindings')
    return {'coordinates':coordinates, 'weights':weights,
            'edges':shared_edges(objects, identities, attribute),
            'identities':identities, 'group_names':names}


def write_shared_weights(objects, surface, weights, changed_mask, *, attribute=SOURCE_ATTRIBUTE):
    names = require_group_names(surface['group_names'])
    identities = np.asarray(surface['identities'])
    weights = np.asarray(weights, dtype=float)
    changed_mask = np.asarray(changed_mask)
    if identities.ndim != 1 or not len(identities) or not np.issubdtype(identities.dtype, np.integer):
        raise ValueError('Shared identities must be a nonempty integer vector')
    if (identities < 0).any() or (np.diff(identities) <= 0).any():
        raise ValueError('Shared identities must be sorted, unique and nonnegative')
    if weights.shape != (len(identities), len(names)) or changed_mask.shape != (len(identities),):
        raise ValueError('New bindings and mask must match the shared surface')
    if changed_mask.dtype != bool or not np.isfinite(weights).all() or (weights < 0).any():
        raise ValueError('Provide a Boolean mask and finite nonnegative weights')
    if not np.allclose(weights.sum(axis=1), 1, atol=WEIGHT_SUM_TOLERANCE, rtol=0):
        raise ValueError('New bindings must be normalized')
    targets = []
    for obj in objects:
        original_ids = source_ids(obj, attribute)
        ids = np.searchsorted(identities, original_ids)
        if (ids >= len(identities)).any() or not np.array_equal(identities[ids], original_ids):
            raise ValueError('Object identities do not match the collected surface')
        targets.append((obj, ids, np.flatnonzero(changed_mask[ids]).tolist()))
    for obj, ids, selected in targets:
        if not selected:
            continue
        groups = [obj.vertex_groups.get(name) or obj.vertex_groups.new(name=name) for name in names]
        for group in groups:
            group.remove(selected)
        for vertex in selected:
            for column in np.flatnonzero(weights[ids[vertex]]):
                groups[int(column)].add([vertex], float(weights[ids[vertex], column]), 'REPLACE')


def evaluated_seams(objects, *, space_matrix, depsgraph=None, attribute=SOURCE_ATTRIBUTE):
    import bpy
    graph = depsgraph if depsgraph is not None else bpy.context.evaluated_depsgraph_get()
    inverse_space = space_matrix.inverted()
    seen = {}
    maximum = 0.0
    shared = 0
    for obj in objects:
        original_ids = source_ids(obj, attribute)
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        try:
            layer = mesh.attributes.get(attribute)
            if (layer is None or layer.domain != 'POINT' or layer.data_type != 'INT'
                    or len(mesh.vertices) != len(original_ids)):
                raise ValueError('Topology-changing modifiers require a new shared correspondence')
            ids = np.empty(len(mesh.vertices), dtype=np.int32)
            layer.data.foreach_get('value', ids)
            if not np.array_equal(ids, original_ids):
                raise ValueError('Evaluated source identities no longer match the rest surface')
            positions = mesh_coordinates(mesh, inverse_space @ evaluated.matrix_world)
            if not np.isfinite(positions).all():
                raise ValueError('Evaluated positions must be finite')
            for position, identity in zip(positions, ids):
                if int(identity) in seen:
                    maximum = max(maximum, float(np.linalg.norm(seen[int(identity)] - position)))
                    shared += 1
                else:
                    seen[int(identity)] = position
        finally:
            evaluated.to_mesh_clear()
    return {'shared_instances':shared, 'max_position_error':maximum}
