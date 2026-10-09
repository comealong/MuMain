"""Close views of knee and ankle junctions, retaining the existing lighting."""
from pathlib import Path
import bpy
from mathutils import Vector

OUT = Path(r'E:/Projects/MuMain/tools/art_pipeline/workspace/characters/chibi_joint_blend_20261009')
CENTER = Vector((75, 0, 24))
VIEWS = {'front': (115, -440, 55), 'side': (420, -190, 47)}


def render_joint_views(prefix):
    scene = bpy.context.scene
    reference = bpy.data.collections['Original_Reference']
    previous_visibility = reference.hide_render
    reference.hide_render = True
    scene.render.engine = 'BLENDER_WORKBENCH'
    shading = scene.display.shading
    shading.light = 'STUDIO'
    shading.studio_light = 'paint.sl'
    shading.show_cavity = False
    shading.show_shadows = True
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.camera.data.ortho_scale = 86
    for label, position in VIEWS.items():
        scene.camera.location = position
        scene.camera.rotation_euler = (CENTER - scene.camera.location).to_track_quat('-Z', 'Y').to_euler()
        for material in ('TEXTURE', 'SINGLE'):
            shading.color_type = material
            shading.single_color = (.55, .55, .55)
            scene.render.filepath = str(OUT / 'previews' / f'{prefix}_{label}_{material.lower()}.png')
            bpy.ops.render.render(write_still=True)
    shading.color_type = 'TEXTURE'
    reference.hide_render = previous_visibility


if __name__ == '__main__':
    render_joint_views('before')
