"""Repair skin weights on a shared surface with explicit fixed/free regions."""
from __future__ import annotations

import numpy as np

DEFAULT_MAX_ITERATIONS = 1500
DEFAULT_RELATIVE_TOLERANCE = 1e-7
WEIGHT_SUM_TOLERANCE = 1e-5
NEGATIVE_ROUNDOFF_TOLERANCE = 1e-6


def validate_inputs(coordinates, weights, edges, free_mask, min_edge_length):
    coordinates = np.asarray(coordinates, dtype=float)
    weights = np.asarray(weights, dtype=float)
    edges = np.asarray(edges)
    free_mask = np.asarray(free_mask)
    if coordinates.ndim != 2 or coordinates.shape[1] != 3:
        raise ValueError('Coordinates must have shape (vertices, 3)')
    if weights.ndim != 2 or weights.shape[0] != len(coordinates) or not weights.shape[1]:
        raise ValueError('Weights must have one row per vertex and at least one channel')
    if edges.ndim != 2 or edges.shape[1] != 2 or not np.issubdtype(edges.dtype, np.integer):
        raise ValueError('Edges must be integer vertex pairs')
    if free_mask.shape != (len(coordinates),) or free_mask.dtype != bool:
        raise ValueError('Free mask must be a Boolean value for each vertex')
    if not np.isfinite(coordinates).all() or not np.isfinite(weights).all():
        raise ValueError('Coordinates and weights must be finite')
    if (weights < 0).any() or not np.allclose(weights.sum(axis=1), 1, atol=WEIGHT_SUM_TOLERANCE, rtol=0):
        raise ValueError('Input bindings must be nonnegative and normalized')
    if not np.isfinite(min_edge_length) or min_edge_length <= 0:
        raise ValueError('Minimum edge length must be finite and positive')
    if edges.size and ((edges < 0).any() or (edges >= len(coordinates)).any()):
        raise ValueError('Edge indices are outside the vertex array')
    if edges.size and (edges[:, 0] == edges[:, 1]).any():
        raise ValueError('Self edges are not valid surface neighbors')
    edges = np.unique(np.sort(edges, axis=1), axis=0)
    return coordinates, weights, edges, free_mask


def find_component(parent, vertex):
    while parent[vertex] != vertex:
        parent[vertex] = parent[parent[vertex]]
        vertex = parent[vertex]
    return vertex


def require_fixed_boundaries(edges, free_mask):
    lookup = np.full(len(free_mask), -1, dtype=int)
    lookup[free_mask] = np.arange(free_mask.sum())
    parent = np.arange(free_mask.sum())
    internal = edges[np.all(free_mask[edges], axis=1)]
    for first, second in lookup[internal]:
        left = find_component(parent, first)
        right = find_component(parent, second)
        if left != right:
            parent[right] = left
    boundary = edges[np.logical_xor(free_mask[edges[:, 0]], free_mask[edges[:, 1]])]
    anchored = {find_component(parent, lookup[vertex])
                for pair in boundary for vertex in pair if free_mask[vertex]}
    roots = {find_component(parent, vertex) for vertex in range(len(parent))}
    if not roots.issubset(anchored):
        raise ValueError('Every free component must connect to a fixed binding')


def laplacian_system(coordinates, weights, edges, free_mask, min_edge_length):
    selected = edges[np.any(free_mask[edges], axis=1)]
    origins = np.concatenate((selected[:, 0], selected[:, 1]))
    neighbors = np.concatenate((selected[:, 1], selected[:, 0]))
    keep = free_mask[origins]
    origins, neighbors = origins[keep], neighbors[keep]
    lengths = np.linalg.norm(coordinates[origins] - coordinates[neighbors], axis=1)
    conductance = 1 / np.maximum(lengths, min_edge_length)
    lookup = np.full(len(coordinates), -1, dtype=int)
    lookup[free_mask] = np.arange(free_mask.sum())
    rows = lookup[origins]
    diagonal = np.bincount(rows, weights=conductance, minlength=free_mask.sum())
    internal = free_mask[neighbors]
    boundary = ~internal
    rhs = np.zeros((free_mask.sum(), weights.shape[1]))
    for column in range(weights.shape[1]):
        rhs[:, column] = np.bincount(rows[boundary],
            weights=conductance[boundary] * weights[neighbors[boundary], column],
            minlength=free_mask.sum())
    return diagonal, rows[internal], lookup[neighbors[internal]], conductance[internal], rhs


def multiply_laplacian(values, diagonal, rows, neighbors, conductance):
    result = diagonal[:, None] * values
    for column in range(values.shape[1]):
        result[:, column] -= np.bincount(rows,
            weights=conductance * values[neighbors, column], minlength=len(values))
    return result


def conjugate_gradient(initial, system, max_iterations, relative_tolerance):
    diagonal, rows, neighbors, conductance, rhs = system
    multiply = lambda values: multiply_laplacian(values, diagonal, rows, neighbors, conductance)
    values = initial.copy()
    residual = rhs - multiply(values)
    direction = residual / diagonal[:, None]
    products = (residual * direction).sum(axis=0)
    reference = np.maximum(np.linalg.norm(rhs, axis=0), 1)
    relative = np.linalg.norm(residual, axis=0) / reference
    iterations = 0
    while float(relative.max()) > relative_tolerance and iterations < max_iterations:
        active = relative > relative_tolerance
        direction[:, ~active] = 0
        applied = multiply(direction)
        denominator = (direction * applied).sum(axis=0)
        if (denominator[active] <= 0).any():
            raise RuntimeError('The surface weight system lost positive definiteness')
        step = np.divide(products, denominator, out=np.zeros_like(products), where=active)
        values += direction * step
        residual -= applied * step
        preconditioned = residual / diagonal[:, None]
        next_products = (residual * preconditioned).sum(axis=0)
        ratio = np.divide(next_products, products, out=np.zeros_like(products), where=active)
        direction = preconditioned + direction * ratio
        products = next_products
        relative = np.linalg.norm(residual, axis=0) / reference
        iterations += 1
    if not np.isfinite(values).all() or float(relative.max()) > relative_tolerance:
        raise RuntimeError('Surface weight solve did not converge')
    return values, iterations, float(relative.max())


def solve_surface_weights(coordinates, weights, edges, free_mask, *, min_edge_length,
                          max_iterations=DEFAULT_MAX_ITERATIONS,
                          relative_tolerance=DEFAULT_RELATIVE_TOLERANCE):
    coordinates, weights, edges, free_mask = validate_inputs(
        coordinates, weights, edges, free_mask, min_edge_length)
    if not isinstance(max_iterations, int) or max_iterations <= 0:
        raise ValueError('Maximum iterations must be a positive integer')
    if not np.isfinite(relative_tolerance) or relative_tolerance <= 0:
        raise ValueError('Relative tolerance must be finite and positive')
    if not free_mask.any():
        return weights.copy(), {'free_vertices':0, 'iterations':0, 'relative_residual':0.0}
    require_fixed_boundaries(edges, free_mask)
    system = laplacian_system(coordinates, weights, edges, free_mask, min_edge_length)
    current, iterations, residual = conjugate_gradient(
        weights[free_mask], system, max_iterations, relative_tolerance)
    if float(current.min()) < -NEGATIVE_ROUNDOFF_TOLERANCE:
        raise RuntimeError('Solved bindings contain significant negative weights')
    current = np.maximum(current, 0)
    totals = current.sum(axis=1)
    if (totals <= 0).any():
        raise RuntimeError('Solved bindings have zero total weight')
    result = weights.copy()
    result[free_mask] = current / totals[:, None]
    return result, {'free_vertices':int(free_mask.sum()), 'iterations':iterations,
                    'relative_residual':residual}


def deformation_metrics(rest, posed, weights, edges):
    rest = np.asarray(rest, dtype=float)
    posed = np.asarray(posed, dtype=float)
    weights = np.asarray(weights, dtype=float)
    edges = np.asarray(edges)
    validate_inputs(rest, weights, edges, np.zeros(len(rest), dtype=bool), 1)
    if posed.shape != rest.shape or not np.isfinite(posed).all():
        raise ValueError('Posed positions must match rest positions and be finite')
    lengths = np.linalg.norm(rest[edges[:, 0]] - rest[edges[:, 1]], axis=1)
    if (lengths <= 0).any():
        raise ValueError('Degenerate rest edges require separate inspection')
    gradients = np.abs(weights[edges[:, 0]] - weights[edges[:, 1]]).sum(axis=1) / lengths
    stretch = np.linalg.norm(posed[edges[:, 0]] - posed[edges[:, 1]], axis=1) / lengths
    return {'weight_gradient':gradients, 'edge_stretch':stretch}
