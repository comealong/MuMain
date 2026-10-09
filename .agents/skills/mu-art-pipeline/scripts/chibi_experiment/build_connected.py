"""Revise the saved chibi experiment without modifying game resources."""
from pathlib import Path
import sys,json,hashlib
import bpy
from mathutils import Vector
ROOT=Path(r'E:/Projects/MuMain')
OUT=Path(r'E:/Projects/MuMain/tools/art_pipeline/workspace/characters/chibi_joint_blend_20261009')
INPUT=Path(r'E:/Projects/MuMain/tools/art_pipeline/workspace/characters/chibi_anatomy_20261009/Chibi_Anatomy_Experiment.blend')
sys.path.insert(0,str(OUT/'scripts'))
sys.path.insert(0,str(ROOT/'.agents/skills/mu-art-pipeline/scripts'))
sys.path.insert(0,str(ROOT/'.agents/skills/mu-art-pipeline/scripts/dwarf_experiment'))
from connected_body import rebuild_body
from mu_art_pipeline.blender_player_rig import select_player_action
from mu_art_pipeline.bmd import parse_bmd
from build_experiment import apply_static_pose

POSES=(('standing',4,0),('walking',17,3),('sword_swing',39,4))


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def configure(scene,center,scale,size):
    scene.render.engine='BLENDER_WORKBENCH'
    scene.display.shading.light='STUDIO';scene.display.shading.studio_light='paint.sl'
    scene.display.shading.color_type='TEXTURE';scene.display.shading.show_cavity=False
    scene.display.shading.show_shadows=True
    scene.render.resolution_x,scene.render.resolution_y=size
    scene.render.resolution_percentage=100
    scene.camera.data.ortho_scale=scale
    scene.camera.location=(center[0]+55,center[1]-650,center[2]+130)
    scene.camera.rotation_euler=(Vector(center)-scene.camera.location).to_track_quat('-Z','Y').to_euler()


def original_pose(index,key):
    rig=bpy.data.objects['Original_Reference_Armature']
    player=parse_bmd(Path(r'E:/Projects/MuMain/tools/art_pipeline/workspace/characters/dwarf_weapon_attachment_fixed_20261009/sources/player.bmd'))
    names=[next(b.name for b in rig.data.bones if b.get('mu_bmd_node')==i) for i in range(60)]
    apply_static_pose(player,rig,names,index,key)


def render_views(rig,original):
    scene=bpy.context.scene
    actions={a['mu_bmd_action_index']:a for a in bpy.data.actions if a.name.startswith('Chibi_')}
    configure(scene,(0,0,90),350,(1600,1100))
    for name,index,key in POSES:
        select_player_action(rig,actions[index],key+1);original_pose(index,key)
        scene.render.filepath=str(OUT/'previews'/f'{name}.png')
        bpy.ops.render.render(write_still=True)
    select_player_action(rig,actions[4]);original_pose(4,0)
    original.hide_render=True
    configure(scene,(75,0,72),178,(1000,1200))
    scene.render.filepath=str(OUT/'previews/Chibi_Portrait.png');bpy.ops.render.render(write_still=True)
    scene.camera.location=(75,-650,240)
    scene.camera.rotation_euler=(Vector((75,0,72))-scene.camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/'previews/Viewport_Angle.png');bpy.ops.render.render(write_still=True)
    configure(scene,(75,0,68),108,(1200,900))
    scene.camera.location=(75,-650,115)
    scene.camera.rotation_euler=(Vector((75,0,68))-scene.camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/'previews/Shoulder_Front.png');bpy.ops.render.render(write_still=True)
    scene.camera.location=(575,-300,115)
    scene.camera.rotation_euler=(Vector((75,0,68))-scene.camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/'previews/Shoulder_Side.png');bpy.ops.render.render(write_still=True)
    original.hide_render=False
    configure(scene,(0,0,90),350,(1600,1100))
    scene.render.filepath=str(OUT/'previews/Original_vs_Chibi.png');bpy.ops.render.render(write_still=True)


def save_scene(rig):
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                space=area.spaces.active
                space.shading.type='SOLID';space.shading.color_type='TEXTURE';space.shading.light='STUDIO';space.shading.studio_light='paint.sl'
                space.shading.show_cavity=False;space.overlay.show_wireframes=False
                space.region_3d.view_location=(0,0,90);space.region_3d.view_distance=370
                space.region_3d.view_rotation=bpy.context.scene.camera.rotation_euler.to_quaternion()
    for obj in bpy.context.selected_objects:obj.select_set(False)
    rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.context.scene['mu_connected_body_experiment']=True
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Chibi_Joint_Blend_Experiment.blend'))


def main():
    before=digest(INPUT)
    collection=bpy.data.collections['Chibi_Dwarf'];rig=bpy.data.objects['Chibi_Dwarf_Armature']
    objects={o.get('mu_bmd_source_file'):o for o in collection.objects if o.get('mu_bmd_source_file')}
    image=bpy.data.images['chibi_skin.png'];image.filepath=str(OUT/'textures/chibi_skin.png');image.pack()
    painted=bpy.data.materials['Chibi_Painted_Skin'];cuff=bpy.data.materials['Chibi_Silver_Cuffs']
    glove=bpy.data.materials["Chibi_Charcoal_Leather"]
    materials=[painted,painted,glove,cuff,painted,painted,cuff]
    details=rebuild_body(rig,collection,objects,materials)
    details["revision"]="Continuous knee rings and extended ankle-to-instep envelope; rest rig unchanged"
    from joint_views import render_joint_views
    render_joint_views("after")
    render_views(rig,bpy.data.collections['Original_Reference'])
    save_scene(rig)
    report={'source_blend':str(INPUT),'source_blend_sha256':before,'source_blend_unchanged':digest(INPUT)==before,
            'actions':len([a for a in bpy.data.actions if a.name.startswith('Chibi_')]),'bones':len(rig.data.bones),
            'body_parts':len(objects),'geometry':details,'textures_packed':True,'original_visible':True,
            'weapon_node':33,'installed_to_game':False,'visual_poses':[{'action':i,'key':k} for _,i,k in POSES],
            'limit':'Blender art prototype; all-action visual review and game export not performed'}
    (OUT/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
