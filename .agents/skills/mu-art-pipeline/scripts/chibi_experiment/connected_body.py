"""Author connected body volumes and retain four separate rigged body slots."""
import math
import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from surface import Surface, unit, smoothstep, add_cuff, add_hand

VOXEL_SIZE = 0.42
SMOOTH_ITERATIONS = 4
WEIGHT_ITERATIONS = 6
ARM_ROOT_DEPTH = 6.0
ARM_ROOT_WIDTH_FACTOR = .80
DELTOID_LOWERING = 3.2
BICEPS_FLARE = 1.0
ARM_STEPS = 49
CURVE_STEPS_PER_SEGMENT = 12
ARM_RADIUS_KNOTS = (0,.55,1,1.8,2.5,3,3.35,4)
ARM_RADII = (3.8,5.2,5.6,5.3,5.0,4.8,5.5,4.1)
STRAP_WIDTH_AT_REFERENCE = 18.6
STRAP_REFERENCE_HEIGHT = 74.0
STRAP_SLOPE = .4
SHOULDER_SCULPT_ITERATIONS = 22

JOINTS = ((26, 27, 28, 33), (35, 36, 37, 42))
LEGS = ((3, 4, 5, 6), (10, 11, 12, 13))
ROLE_SLOT = {0: 'ArmorClass01.bmd', 1: 'GloveClass01.bmd', 2: 'GloveClass01.bmd',
             3: 'GloveClass01.bmd', 4: 'PantClass01.bmd', 5: 'BootClass01.bmd', 6: 'BootClass01.bmd'}


def append_mesh(surface, obj, material_offset):
    offset = len(surface.vertices)
    surface.vertices.extend(tuple(v.co) for v in obj.data.vertices)
    lookup = {g.index: g.name for g in obj.vertex_groups}
    bone_nodes = {b.name: b.get('mu_bmd_node') for b in obj.parent.data.bones}
    for vertex in obj.data.vertices:
        surface.weights.append({bone_nodes[lookup[g.group]]:g.weight for g in vertex.groups})
    for face in obj.data.polygons:
        surface.faces.append(tuple(offset + i for i in face.vertices))
        surface.materials.append(material_offset + face.material_index)


def torso(surface, point):
    pelvis, neck = point(2), point(19)
    waist, top = pelvis[2] - 3.8, neck[2] + 2.0
    heights = np.linspace(waist, top, 33)
    profile_t = [0, .06, .25, .50, .73, .84, .94, 1]
    profile_r = [18, 21, 22, 22, 21.0, 20.5, 15.0, 5]
    centers = [np.array((pelvis[0], neck[1], z)) for z in heights]
    radii = [float(np.interp(i / 32, profile_t, profile_r)) for i in range(33)]
    weights = [{2:1-smoothstep(i/12),18:smoothstep(i/12)} for i in range(33)]
    surface.sweep(centers, radii, weights, [0]*33, depth=.59)



def catmull_point(points,segment,t):
    p0=points[max(segment-1,0)]
    p1=points[segment]
    p2=points[segment+1]
    p3=points[min(segment+2,len(points)-1)]
    return .5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t)


def anatomical_arms(surface,point):
    # A descending shoulder cap, tapered upper arm and a distinct narrow wrist.
    for upper,fore,hand,socket in JOINTS:
        shoulder,elbow,wrist=point(upper),point(fore),point(hand)
        sign=math.copysign(1.,shoulder[0]);clav=upper-1
        root=shoulder+np.array((-sign*14.,0.,0.))
        cap=shoulder+np.array((-sign*.8,0.,-3.0))
        biceps=shoulder*.55+elbow*.45
        controls=[root,cap,biceps,elbow,wrist]
        centers,radii,bindings,materials=[],[],[],[]
        knots=(0,.65,1,1.65,2.5,3,3.28,3.55,4)
        sizes=(3.5,4.6,4.75,4.65,3.85,3.6,4.55,4.1,2.65)
        for step in range(ARM_STEPS):
            value=step/CURVE_STEPS_PER_SEGMENT;segment=min(int(value),3)
            centers.append(catmull_point(controls,segment,value-segment))
            radii.append(float(np.interp(value,knots,sizes)))
            if value<1:
                amount=smoothstep(value)
                binding={18:.4*(1-amount),clav:.6*(1-amount),upper:amount}
            else:
                elbow_blend=smoothstep((value-2.65)/.65)
                wrist_blend=smoothstep((value-3.72)/.28)
                binding={upper:(1-elbow_blend)*(1-wrist_blend),fore:elbow_blend*(1-wrist_blend),hand:wrist_blend}
            bindings.append(binding);materials.append(1 if value<3.05 else 2)
        surface.sweep(centers,radii,bindings,materials,depth=.86)
        direction=unit(wrist-elbow)
        cuff_centers=[elbow+direction*t for t in (.55,.8,1.15,1.6,1.9)]
        surface.sweep(cuff_centers,[4.3,4.9,5.1,4.95,4.55],[{fore:1.}]*5,[3]*5,depth=.91)


from continuous_legs import lower_body, soften_ankle_envelopes


def source_lookup(surface):
    triangles, roles, weights=[] , [], []
    for face, role in zip(surface.faces,surface.materials):
        for i in range(1,len(face)-1):
            triangles.append((face[0],face[i],face[i+1]))
            roles.append(role)
    tree=BVHTree.FromPolygons(surface.vertices,triangles,all_triangles=True)
    return tree,triangles,roles


def remesh_volume(surface, collection):
    mesh=bpy.data.meshes.new('Connected_Body_Source')
    mesh.from_pydata(surface.vertices,[],surface.faces);mesh.update()
    edit=bmesh.new();edit.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(edit,faces=list(edit.faces))
    edit.to_mesh(mesh);edit.free()
    obj=bpy.data.objects.new('Body_Sculpt_Working',mesh);collection.objects.link(obj)
    for selected in bpy.context.selected_objects:selected.select_set(False)
    obj.select_set(True);bpy.context.view_layer.objects.active=obj
    obj.data.remesh_voxel_size=VOXEL_SIZE
    bpy.ops.object.voxel_remesh()
    smooth=obj.modifiers.new('Sculpt Surface Relax','SMOOTH');smooth.factor=.28;smooth.iterations=SMOOTH_ITERATIONS
    bpy.ops.object.modifier_apply(modifier=smooth.name)
    return obj



def sculpt_shoulder_blends(obj,point):
    group=obj.vertex_groups.new(name='Shoulder_Sculpt_Mask')
    for vertex in obj.data.vertices:
        x,y,z=vertex.co
        side=smoothstep((abs(x)-12.0)/7.0)
        top=smoothstep((z-65.0)/7.0)*(1-smoothstep((z-81.0)/5.0))
        center=(point(26) if x<0 else point(35)).copy()
        center[0]-=math.copysign(5.0,center[0]);center[2]-=2.0
        distance=float(np.linalg.norm(np.array(vertex.co)-center))
        weight=side*top*(1-smoothstep((distance-7.0)/9.0))
        if weight>0:group.add([vertex.index],weight,'REPLACE')
    modifier=obj.modifiers.new('Sculpt Shoulder To Chest','SMOOTH')
    modifier.factor=.65;modifier.iterations=SHOULDER_SCULPT_ITERATIONS;modifier.vertex_group=group.name
    bpy.context.view_layer.objects.active=obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    current=obj.vertex_groups.get('Shoulder_Sculpt_Mask')
    if current is not None:obj.vertex_groups.remove(current)


def sample_weights(surface, tree, triangles, mesh, bone_count):
    result=np.zeros((len(mesh.vertices),bone_count))
    for vertex in mesh.vertices:
        location,normal,index,distance=tree.find_nearest(vertex.co)
        tri=triangles[index]
        distances=np.array([max((np.array(surface.vertices[i])-np.array(location))@ (np.array(surface.vertices[i])-np.array(location)),.01) for i in tri])
        factors=1/distances;factors/=factors.sum()
        for i,factor in zip(tri,factors):
            for node,weight in surface.weights[i].items():result[vertex.index,node]+=factor*weight
    edges=np.array([e.vertices[:] for e in mesh.edges])
    counts=np.bincount(edges.flatten(),minlength=len(mesh.vertices))[:,None]
    for _ in range(WEIGHT_ITERATIONS):
        neighbors=np.zeros_like(result)
        np.add.at(neighbors,edges[:,0],result[edges[:,1]])
        np.add.at(neighbors,edges[:,1],result[edges[:,0]])
        result=.55*result+.45*neighbors/np.maximum(counts,1)
    result[result<.005]=0
    result/=result.sum(axis=1)[:,None]
    return result


def surface_uv(position, role, point):
    x,y,z=position
    if role==0:
        waist,top=point(2)[2]-3.8,point(19)[2]+2
        u=.125+.105*(np.clip(x/24,-1,1)+1)
        v=.018+.205*(1-np.clip((z-waist)/(top-waist),0,1))
        if y>point(19)[1]:v+=.25
        return (u,1-v)
    if role==1:return (.385,.875)
    if role in (2,3):return (.52,.67)
    leg=LEGS[0] if x>0 else LEGS[1]
    thigh,calf,foot,toe=leg
    center=point(calf)
    phi=(math.atan2(y-center[1],x-center[0])+math.pi)/math.tau
    if role==4:
        t=np.clip((z-point(calf)[2])/(point(2)[2]+7-point(calf)[2]),0,1)
        return (.02+.19*phi,1-(.49+.31*(1-t)))
    t=np.clip(z/point(calf)[2],0,1)
    return (.745+.205*phi,1-(.34+.33*(1-t)))



def relax_material_borders(mesh, roles):
    incident={tuple(sorted(e.vertices)):[] for e in mesh.edges}
    for face,role in zip(mesh.polygons,roles):
        for a,b in zip(face.vertices,tuple(face.vertices[1:])+(face.vertices[0],)):
            incident[tuple(sorted((a,b)))].append(role)
    adjacency={}
    for (a,b), face_roles in incident.items():
        if len(set(face_roles))<2:continue
        adjacency.setdefault(a,set()).add(b);adjacency.setdefault(b,set()).add(a)
    coordinates=np.array([tuple(v.co) for v in mesh.vertices])
    for _ in range(12):
        previous=coordinates.copy()
        for vertex,neighbors in adjacency.items():
            if len(neighbors)==2:
                coordinates[vertex]=.45*previous[vertex]+.55*previous[list(neighbors)].mean(axis=0)
    for vertex in mesh.vertices:vertex.co=coordinates[vertex.index]
    mesh.update()


def split_slots(working, rig, objects, weights, roles, materials, point):
    mesh=working.data
    mesh.update()
    whole_normals=[tuple(v.normal) for v in mesh.vertices]
    for slot,obj in objects.items():
        if slot=='HelmClass01.bmd':continue
        selected=[face for face,role in zip(mesh.polygons,roles) if ROLE_SLOT[role]==slot]
        used=sorted({i for face in selected for i in face.vertices})
        remap={old:new for new,old in enumerate(used)}
        fresh=bpy.data.meshes.new('Connected_'+slot)
        fresh.from_pydata([tuple(mesh.vertices[i].co) for i in used],[],[[remap[i] for i in f.vertices] for f in selected]);fresh.update()
        for mat in materials:fresh.materials.append(mat)
        layer=fresh.uv_layers.new(name='UVMap');loop_normals=[]
        for face,source_face in zip(fresh.polygons,selected):
            role=roles[source_face.index];face.material_index=role;face.use_smooth=True
            for loop,source_index in zip(face.loop_indices,source_face.vertices):
                layer.data[loop].uv=surface_uv(mesh.vertices[source_index].co,role,point)
                loop_normals.append(whole_normals[source_index])
        ids=fresh.attributes.new('mu_connected_source_vertex','INT','POINT')
        for new,old in enumerate(used):ids.data[new].value=old
        fresh.normals_split_custom_set(loop_normals)
        obj.data=fresh
        for mod in list(obj.modifiers):obj.modifiers.remove(mod)
        mod=obj.modifiers.new('Shared Player Skeleton','ARMATURE');mod.object=rig;mod.use_deform_preserve_volume=True
        obj.vertex_groups.clear()
        groups={b.get('mu_bmd_node'):obj.vertex_groups.new(name=b.name) for b in rig.data.bones}
        for old,new in remap.items():
            for node in np.flatnonzero(weights[old]):groups[int(node)].add([new],float(weights[old,node]),'REPLACE')
        obj['mu_connected_surface']=True
        obj['mu_surface_part']=slot
    bpy.data.objects.remove(working,do_unlink=True)


def rebuild_body(rig,collection,objects,materials):
    point=lambda node:np.array(next(b for b in rig.data.bones if b.get('mu_bmd_node')==node).matrix_local.translation)
    surface=Surface();torso(surface,point)
    anatomical_arms(surface,point)
    from arm_anatomy import add_hands
    add_hands(surface,rig,point)
    lower_body(surface,point)
    tree,triangles,source_roles=source_lookup(surface)
    working=remesh_volume(surface,collection)
    sculpt_shoulder_blends(working,point)
    soften_ankle_envelopes(working,point)
    roles=[]
    for face in working.data.polygons:
        _,_,index,_=tree.find_nearest(face.center)
        role=source_roles[index]
        x,y,z=face.center
        # The vest shoulder straps follow the connected upper body surface.
        if role==1 and abs(x)<STRAP_WIDTH_AT_REFERENCE+STRAP_SLOPE*(z-STRAP_REFERENCE_HEIGHT):
            role=0
        roles.append(role)
    relax_material_borders(working.data,roles)
    weights=sample_weights(surface,tree,triangles,working.data,len(rig.data.bones))
    split_slots(working,rig,objects,weights,roles,materials,point)
    return {'source_surfaces_fused':True,'internal_overlaps_removed':True,'voxel_size':VOXEL_SIZE,'shared_seam_weights_and_normals':True}
