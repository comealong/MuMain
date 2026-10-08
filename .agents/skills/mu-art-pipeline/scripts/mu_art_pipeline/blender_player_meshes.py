"""Build independent player body meshes bound to one shared armature."""
from __future__ import annotations

import bpy
from mathutils import Vector

from .poses import validate_part_bones


def create_skin_material(texture_path):
    material = bpy.data.materials.new('MU_Player_Skin')
    material.use_nodes = True
    material['mu_bmd_texture_file'] = texture_path.name
    nodes, links = material.node_tree.nodes, material.node_tree.links
    shader = nodes.get('Principled BSDF')
    shader.inputs['Roughness'].default_value = 0.78
    image = bpy.data.images.load(str(texture_path), check_existing=True)
    image.pack()
    texture = nodes.new('ShaderNodeTexImage')
    texture.image = image
    uv = nodes.new('ShaderNodeUVMap')
    uv.uv_map = 'UVMap'
    links.new(uv.outputs['UV'], texture.inputs['Vector'])
    links.new(texture.outputs['Color'], shader.inputs['Base Color'])
    nodes.active = texture
    return material


def store_vertex_attributes(mesh, item: dict, positions: list):
    original = mesh.attributes.new('mu_bmd_source_position', 'FLOAT_VECTOR', 'POINT')
    nodes = mesh.attributes.new('mu_bmd_source_node', 'INT', 'POINT')
    base = mesh.attributes.new('mu_bmd_base_position', 'FLOAT_VECTOR', 'POINT')
    for index, vertex in enumerate(item['vertices']):
        original.data[index].vector = vertex['position']
        nodes.data[index].value = vertex['node']
        base.data[index].vector = positions[index]


def create_uv_and_normals(mesh, item: dict, rig, names: list[str]):
    layer = mesh.uv_layers.new(name='UVMap')
    source = mesh.attributes.new('mu_bmd_source_normal', 'FLOAT_VECTOR', 'CORNER')
    nodes = mesh.attributes.new('mu_bmd_source_normal_node', 'INT', 'CORNER')
    normals = []
    for polygon, triangle in zip(mesh.polygons, item['triangles']):
        for corner, loop in enumerate(polygon.loop_indices):
            u, v = item['uvs'][triangle['uvs'][corner]]
            layer.data[loop].uv = (u, 1.0 - v)
            normal = item['normals'][triangle['normals'][corner]]
            source.data[loop].vector = normal['normal']
            nodes.data[loop].value = normal['node']
            rotation = rig.data.bones[names[normal['node']]].matrix_local.to_3x3()
            normals.append(tuple((rotation @ Vector(normal['normal'])).normalized()))
        polygon.use_smooth = True
    mesh.normals_split_custom_set(normals)


def bind_mesh(item: dict, name: str, rig, names: list[str], collection, material):
    positions = [tuple(rig.data.bones[names[v['node']]].matrix_local @ Vector(v['position']))
                 for v in item['vertices']]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(positions, [], [t['vertices'] for t in item['triangles']])
    mesh.update()
    store_vertex_attributes(mesh, item, positions)
    create_uv_and_normals(mesh, item, rig, names)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.parent = rig
    modifier = obj.modifiers.new('Shared Player Skeleton', 'ARMATURE')
    modifier.object = rig
    modifier.use_deform_preserve_volume = False
    for index, bone_name in enumerate(names):
        group = obj.vertex_groups.new(name=bone_name)
        vertices = [i for i, v in enumerate(item['vertices']) if v['node'] == index]
        if vertices:
            group.add(vertices, 1.0, 'REPLACE')
    mesh.materials.append(material)
    obj['mu_bmd_uv_convention'] = 'blender_bottom_left'
    obj['mu_character_group'] = collection.name
    return obj


def create_body_parts(parts: list, player: dict, rig, names: list[str], collection, material):
    objects = []
    for part_name, part in parts:
        validate_part_bones(part, player)
        for index, item in enumerate(part['meshes']):
            if item['texture'] != material['mu_bmd_texture_file']:
                raise ValueError(f'{part_name}: unexpected texture {item["texture"]}')
            name = part_name if len(part['meshes']) == 1 else f'{part_name}_{index:02}'
            obj = bind_mesh(item, name, rig, names, collection, material)
            obj['mu_bmd_source'] = part['name']
            obj['mu_bmd_source_file'] = part_name + '.bmd'
            obj['mu_bmd_version'] = part['version']
            obj['mu_bmd_mesh_index'] = index
            objects.append(obj)
    return objects
