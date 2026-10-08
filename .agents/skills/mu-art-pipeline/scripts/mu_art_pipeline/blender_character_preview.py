"""Shared Blender presentation for the Dark Wizard character workflows."""
import bpy
from mathutils import Vector

CAMERA_TARGET = Vector((0, 0, 94))


def create_preview_camera(scene):
    camera_data = bpy.data.cameras.new('PreviewCamera')
    camera = bpy.data.objects.new('PreviewCamera', camera_data)
    scene.collection.objects.link(camera)
    camera_data.type = 'ORTHO'
    camera_data.ortho_scale = 215
    camera.location = (160, -420, 175)
    camera.rotation_euler = (CAMERA_TARGET - camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.camera = camera
    return camera


def configure_preview_viewports(camera):
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                space = area.spaces.active
                space.shading.type = 'SOLID'
                space.shading.color_type = 'TEXTURE'
                space.region_3d.view_location = CAMERA_TARGET
                space.region_3d.view_distance = 270
                space.region_3d.view_rotation = camera.rotation_euler.to_quaternion()


def set_preview_scene(obj):
    scene = bpy.context.scene
    camera = create_preview_camera(scene)
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = 'TEXTURE'
    scene.display.shading.show_shadows = False
    scene.display.shading.background_type = 'WORLD'
    scene.world = bpy.data.worlds.new('PreviewWorld')
    scene.world.color = (0.12, 0.12, 0.12)
    scene.view_settings.view_transform = 'Standard'
    scene.render.resolution_x, scene.render.resolution_y = 800, 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    configure_preview_viewports(camera)
    bpy.context.view_layer.objects.active = obj
    camera.select_set(False)
    obj.select_set(True)
