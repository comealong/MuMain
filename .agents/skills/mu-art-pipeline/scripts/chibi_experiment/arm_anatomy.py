"""Shoulder proportions and oriented gloved hands for the isolated art study."""
import math
import bpy
import numpy as np
from mathutils import Vector
from surface import unit

SHOULDER_INSET = 3.5
SHOULDER_DROP = 2.0
UPPER_ARM_LENGTH = 1.15
FOREARM_LENGTH = 1.25
PALM_RINGS = 18
PALM_SIDES = 28
FINGER_RADIUS = .86
FINGER_SPACING = 1.82
HAND_ROLE = 2


def revise_arm_rest(rig):
    """Keep rest rotations and action delta channels; change local bone offsets."""
    bones = {b.get('mu_bmd_node'): b for b in rig.data.bones}
    old = {i: b.matrix_local.copy() for i, b in bones.items()}
    positions = {i: m.translation.copy() for i, m in old.items()}
    for upper, fore, hand in ((26,27,28),(35,36,37)):
        shoulder = positions[upper] + Vector((-math.copysign(SHOULDER_INSET,positions[upper].x),0,-SHOULDER_DROP))
        elbow = shoulder + (positions[fore]-positions[upper])*UPPER_ARM_LENGTH
        wrist = elbow + (positions[hand]-positions[fore])*FOREARM_LENGTH
        delta = wrist - positions[hand]
        descendants = [bones[hand], *bones[hand].children_recursive]
        for bone in descendants: positions[bone.get('mu_bmd_node')] += delta
        positions[upper], positions[fore] = shoulder, elbow
    for obj in bpy.context.selected_objects: obj.select_set(False)
    rig.select_set(True); bpy.context.view_layer.objects.active=rig
    bpy.ops.object.mode_set(mode='EDIT')
    for node, matrix in old.items():
        matrix.translation = positions[node]
        rig.data.edit_bones[bones[node].name].matrix = matrix
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.update()
    return {'shoulder_inset':SHOULDER_INSET,'shoulder_drop':SHOULDER_DROP,
            'upper_length_factor':UPPER_ARM_LENGTH,'fore_length_factor':FOREARM_LENGTH,
            'rotation_channels_unchanged':True,'retarget':'local rest offsets; existing pose delta channels retained'}


def oriented_volume(surface,center,axes,radii,bone,role):
    """Ellipsoid with explicit palm length, width and thickness axes."""
    offset=len(surface.vertices)
    for ring in range(PALM_RINGS+1):
        theta=math.pi*ring/PALM_RINGS
        for side in range(PALM_SIDES):
            phi=math.tau*side/PALM_SIDES
            p=center+axes[0]*radii[0]*math.cos(theta)
            p+=math.sin(theta)*(axes[1]*radii[1]*math.cos(phi)+axes[2]*radii[2]*math.sin(phi))
            surface.vertices.append(tuple(p));surface.weights.append({bone:1.0})
    for ring in range(PALM_RINGS):
        for side in range(PALM_SIDES):
            a=offset+ring*PALM_SIDES+side;b=offset+ring*PALM_SIDES+(side+1)%PALM_SIDES
            surface.faces.append((a,b,b+PALM_SIDES,a+PALM_SIDES));surface.materials.append(role)


def curved_digit(surface,controls,radius,bone):
    """Round continuous finger, with tapered endpoints and two curved joints."""
    from connected_body import catmull_point
    steps=25
    centers=[];radii=[]
    for i in range(steps):
        t=i/(steps-1)*(len(controls)-1);segment=min(int(t),len(controls)-2)
        centers.append(catmull_point(controls,segment,t-segment))
        radii.append(radius*float(np.interp(i/(steps-1),[0,.12,.55,.88,1],[.85,1,1,.86,.12])))
    surface.sweep(centers,radii,[{bone:1.0}]*steps,[HAND_ROLE]*steps,depth=1)


def holding_hand(surface,rig,point):
    bone=next(b for b in rig.data.bones if b.get('mu_bmd_node')==33)
    rotation=np.array(bone.matrix_local.to_3x3());origin=point(33)
    local=lambda x,y,z:origin+rotation@np.array((x,y,z))
    axes=(rotation[:,2],rotation[:,1],rotation[:,0])
    oriented_volume(surface,local(-1.4,.6,3.2),axes,(3.5,3.55,1.7),28,HAND_ROLE)
    for index in range(4):
        y=(index-1.5)*FINGER_SPACING
        controls=[local(-2.0,y,3.3),local(-2.7,y,.8),local(-2.2,y,-2.1),local(.3,y,-3.2),local(2.4,y,-1.2)]
        curved_digit(surface,controls,FINGER_RADIUS,28)
    thumb=[local(-1.2,-2.1,5.0),local(.9,-3.8,3.6),local(2.4,-3.3,1.8),local(2.8,-1.2,.9)]
    curved_digit(surface,thumb,1.18,28)


def relaxed_hand(surface,rig,point):
    bone=next(b for b in rig.data.bones if b.get('mu_bmd_node')==37)
    rotation=np.array(bone.matrix_local.to_3x3())
    direction=unit(np.array((.15,-.45,-.90)))
    width=unit(np.cross(direction,(0.,1.,0.)))
    normal=unit(np.cross(width,direction))
    wrist=point(37)
    local=lambda length,side,depth:wrist+direction*length+width*side+normal*depth
    oriented_volume(surface,local(3.5,0,0),(direction,width,normal),(4.1,3.65,1.95),37,HAND_ROLE)
    for index,length in enumerate((3.5,4.4,4.1,3.1)):
        side=(index-1.5)*1.85
        controls=[local(5.6,side,0),local(7.0,side,-.2),local(6.4+length*.65,side,.7),local(6.3+length*.65,side,2.3)]
        curved_digit(surface,controls,.86,37)
    thumb=[local(2.0,-2.2,.1),local(3.7,-4.1,.5),local(5.5,-4.0,1.5),local(6.2,-3.4,2.1)]
    curved_digit(surface,thumb,1.04,37)


def add_hands(surface,rig,point):
    holding_hand(surface,rig,point)
    relaxed_hand(surface,rig,point)
