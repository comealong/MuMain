"""Restore Corrected UVs from source BMDs using Blender's image origin."""
from pathlib import Path
from datetime import datetime
import json
import shutil
import sys
import bpy
from mathutils import Vector

PARTS = ('HelmClass01', 'ArmorClass01', 'PantClass01', 'GloveClass01', 'BootClass01')
OBJECT_NAME = 'DarkWizard_Initial_Corrected'
ROOT = Path(__file__).resolve().parents[4]
WORKSPACE = ROOT / 'tools/art_pipeline/workspace'
PLAYER = WORKSPACE / 'Player'
sys.path.insert(0, str(ROOT / '.agents/skills/mu-art-pipeline/scripts'))
from mu_art_pipeline.bmd import parse_bmd


def source_meshes():
    return [(name, parse_bmd(PLAYER / (name + '.bmd'))['meshes'][0]) for name in PARTS]


def verify_topology(obj, meshes):
    expected_vertices = sum(len(mesh['vertices']) for _, mesh in meshes)
    expected_faces = sum(len(mesh['triangles']) for _, mesh in meshes)
    if len(obj.data.vertices) != expected_vertices or len(obj.data.polygons) != expected_faces:
        raise ValueError('Corrected topology no longer matches the source parts.')
    offset = 0
    polygon_index = 0
    for name, mesh in meshes:
        for triangle in mesh['triangles']:
            actual = tuple(obj.data.polygons[polygon_index].vertices)
            expected = tuple(offset + index for index in triangle['vertices'])
            if actual != expected:
                raise ValueError(f'{name}: polygon {polygon_index} vertex order mismatch: {actual} != {expected}')
            polygon_index += 1
        offset += len(mesh['vertices'])


def restore_uvs(obj, meshes):
    layer = obj.data.uv_layers.active or obj.data.uv_layers.new(name='UVMap')
    polygon_index = 0
    corner_count = 0
    for _, mesh in meshes:
        for triangle in mesh['triangles']:
            polygon = obj.data.polygons[polygon_index]
            for loop_index, uv_index in zip(polygon.loop_indices, triangle['uvs']):
                u, v = mesh['uvs'][uv_index]
                layer.data[loop_index].uv = (u, 1.0 - v)
                corner_count += 1
            polygon_index += 1
    obj['mu_bmd_uv_convention'] = 'blender_bottom_left'
    obj['mu_uv_source'] = 'Source BMD face-corner UV: Blender U=MU U, Blender V=1-MU V'
    obj.data.update()
    return corner_count


def restore_obj_uvs(meshes):
    path = PLAYER / (OBJECT_NAME + '.obj')
    mesh_by_name = dict(meshes)
    lines = path.read_text(encoding='utf-8-sig').splitlines()
    result = []
    group = None
    uv_index = 0
    for line in lines:
        if line.startswith('g '):
            if group is not None and uv_index != len(mesh_by_name[group]['uvs']):
                raise ValueError(f'{group}: OBJ UV record count mismatch')
            group = line[2:].strip()
            uv_index = 0
        if line.startswith('vt '):
            u, v = mesh_by_name[group]['uvs'][uv_index]
            line = f'vt {u:.9g} {1.0-v:.9g}'
            uv_index += 1
        result.append(line)
    if uv_index != len(mesh_by_name[group]['uvs']):
        raise ValueError(f'{group}: final OBJ UV record count mismatch')
    path.write_text('\n'.join(result) + '\n', encoding='utf-8')


def configure_material(obj):
    image = bpy.data.images.load(str(PLAYER / 'skin_barbarian_01.jpg'), check_existing=True)
    image.pack()
    mat = bpy.data.materials.get('DarkWizard_Corrected_BMD_Texture') or bpy.data.materials.new('DarkWizard_Corrected_BMD_Texture')
    mat.use_nodes = True
    mat.node_tree.nodes.clear()
    output = mat.node_tree.nodes.new('ShaderNodeOutputMaterial')
    shader = mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
    texture = mat.node_tree.nodes.new('ShaderNodeTexImage')
    coordinates = mat.node_tree.nodes.new('ShaderNodeUVMap')
    coordinates.uv_map = obj.data.uv_layers.active.name
    coordinates.location = (-600, 0)
    texture.location = (-380, 0)
    shader.location = (-60, 0)
    output.location = (260, 0)
    texture.image = image
    mat.node_tree.nodes.active = texture
    shader.inputs['Roughness'].default_value = 0.78
    mat.node_tree.links.new(coordinates.outputs['UV'], texture.inputs['Vector'])
    mat.node_tree.links.new(texture.outputs['Color'], shader.inputs['Base Color'])
    mat.node_tree.links.new(shader.outputs['BSDF'], output.inputs['Surface'])
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    for polygon in obj.data.polygons:
        polygon.material_index = 0
    image.filepath = bpy.path.relpath(str(PLAYER / 'skin_barbarian_01.jpg'))


def focus_model(obj):
    for other in bpy.context.view_layer.objects:
        other.select_set(False)
        if other.name in {'DarkWizard_Initial', 'DarkWizard_Initial_Combined'}:
            other.hide_set(True)
            other.hide_render = True
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    rotation = (Vector((0, 0, 94)) - Vector((255, -420, 220))).to_track_quat('-Z', 'Y')
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                space = area.spaces.active
                space.shading.type = 'MATERIAL'
                space.region_3d.view_location = (0, 0, 94)
                space.region_3d.view_distance = 270
                space.region_3d.view_rotation = rotation


def render_preview():
    scene = bpy.context.scene
    camera_data = bpy.data.cameras.new('UVVerificationCamera')
    camera = bpy.data.objects.new('UVVerificationCamera', camera_data)
    scene.collection.objects.link(camera)
    camera_data.type = 'ORTHO'
    camera_data.ortho_scale = 215
    scene.camera = camera
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = 'TEXTURE'
    scene.display.shading.show_shadows = False
    scene.display.shading.background_type = 'WORLD'
    scene.world.color = (0.12, 0.12, 0.12)
    scene.view_settings.view_transform = 'Standard'
    scene.render.resolution_x = 800
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    for suffix, location in [('', (160, -420, 175)), ('_back', (-160, 420, 175))]:
        camera.location = location
        camera.rotation_euler = (Vector((0, 0, 94)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = str(WORKSPACE / 'previews' / ('dark_wizard_initial_corrected_texture_preview' + suffix + '.png'))
        bpy.ops.render.render(write_still=True)


def main():
    obj = bpy.data.objects[OBJECT_NAME]
    meshes = source_meshes()
    verify_topology(obj, meshes)
    geometry_before = [tuple(vertex.co) for vertex in obj.data.vertices]
    backup = WORKSPACE / 'backups' / ('dark_wizard_uv_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
    backup.mkdir(parents=True, exist_ok=True)
    shutil.copy2(bpy.data.filepath, backup / Path(bpy.data.filepath).name)
    shutil.copy2(PLAYER / (OBJECT_NAME + '.obj'), backup / (OBJECT_NAME + '.obj'))
    corners = restore_uvs(obj, meshes)
    restore_obj_uvs(meshes)
    configure_material(obj)
    focus_model(obj)
    if geometry_before != [tuple(vertex.co) for vertex in obj.data.vertices]:
        raise RuntimeError('Geometry changed unexpectedly')
    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
    print(json.dumps({'saved': bpy.data.filepath, 'corrected_uv_corners': corners, 'geometry_unchanged': True, 'backup': str(backup)}))
    render_preview()

if __name__ == '__main__':
    main()
