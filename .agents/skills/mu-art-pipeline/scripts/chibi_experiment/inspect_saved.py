"""Record connected body topology and shared boundary data from the saved artifact."""
from pathlib import Path
from collections import defaultdict
import json,bpy
OUT=Path(r'E:/Projects/MuMain/tools/art_pipeline/workspace/characters/chibi_joint_blend_20261009')
collection=bpy.data.collections['Chibi_Dwarf']
parts=[o for o in collection.objects if o.type=='MESH' and o.data.attributes.get('mu_connected_source_vertex')]
positions={};bindings={};faces=set();duplicates=0;edges=defaultdict(int);adjacency=defaultdict(set)
position_error=0.0;weight_error=0.0;shared=0
for obj in parts:
    ids=[entry.value for entry in obj.data.attributes['mu_connected_source_vertex'].data]
    for vertex,identity in zip(obj.data.vertices,ids):
        weights={obj.vertex_groups[g.group].name:g.weight for g in vertex.groups}
        if identity in positions:
            shared+=1
            position_error=max(position_error,(vertex.co-positions[identity]).length)
            for name in set(weights)|set(bindings[identity]):weight_error=max(weight_error,abs(weights.get(name,0)-bindings[identity].get(name,0)))
        else:positions[identity]=vertex.co.copy();bindings[identity]=weights
    for polygon in obj.data.polygons:
        indices=[ids[i] for i in polygon.vertices]
        signature=tuple(sorted(indices));duplicates+=signature in faces;faces.add(signature)
        for a,b in zip(indices,indices[1:]+indices[:1]):
            edge=tuple(sorted((a,b)));edges[edge]+=1
            adjacency[a].add(b);adjacency[b].add(a)
unvisited=set(positions);components=[]
while unvisited:
    root=next(iter(unvisited));stack=[root];unvisited.remove(root);count=0
    while stack:
        vertex=stack.pop();count+=1
        for neighbor in adjacency[vertex]:
            if neighbor in unvisited:unvisited.remove(neighbor);stack.append(neighbor)
    components.append(count)
rig=bpy.data.objects['Chibi_Dwarf_Armature'];weapon=bpy.data.objects['Chibi_Sword01']
constraint=weapon.parent.constraints[0]
result={'body_surface_components':sorted(components,reverse=True),'duplicate_faces':duplicates,
        'combined_open_boundary_edges':sum(count==1 for count in edges.values()),
        'combined_nonmanifold_edges':sum(count!=2 for count in edges.values()),
        'shared_boundary_vertices':shared,'shared_vertex_position_error':position_error,'shared_vertex_weight_error':weight_error,
        'body_parts':len([o for o in collection.objects if o.get('mu_bmd_source_file')]),
        'actions':len([a for a in bpy.data.actions if a.name.startswith('Chibi_')]),
        'weapon_node':rig.data.bones[constraint.subtarget]['mu_bmd_node'],
        'original_visible':not bpy.data.collections['Original_Reference'].hide_render and not bpy.data.collections['Original_Reference'].hide_viewport,
        'textures':[{'name':im.name,'packed':bool(im.packed_file)} for im in bpy.data.images if im.source=='FILE']}
(OUT/'saved_surface_inspection.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result),flush=True)

# Check the same shared vertices after armature evaluation in selected poses.
import sys
sys.path.insert(0, str(OUT / "scripts"))
sys.path.insert(0, str(Path(r'E:/Projects/MuMain/.agents/skills/mu-art-pipeline/scripts')))
from mu_art_pipeline.blender_player_rig import select_player_action
from joint_views import render_joint_views

POSE_SAMPLES = ((4, 0), (17, 3), (26, 3), (39, 4))
actions = {a['mu_bmd_action_index']: a for a in bpy.data.actions if a.name.startswith('Chibi_')}


def evaluated_seam_error():
    seen = {}
    maximum = 0.0
    graph = bpy.context.evaluated_depsgraph_get()
    for part in parts:
        evaluated = part.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        try:
            identities = mesh.attributes['mu_connected_source_vertex'].data
            for vertex, identity in zip(mesh.vertices, identities):
                position = evaluated.matrix_world @ vertex.co
                if identity.value in seen:
                    maximum = max(maximum, (position - seen[identity.value]).length)
                else:
                    seen[identity.value] = position
        finally:
            evaluated.to_mesh_clear()
    return maximum


samples = []
for action_index, key in POSE_SAMPLES:
    select_player_action(rig, actions[action_index], key + 1)
    samples.append({'action': action_index, 'key': key, 'max_world_seam_error': evaluated_seam_error()})
    if action_index in (17, 39):
        render_joint_views(f'pose_{action_index}')
select_player_action(rig, actions[4], 1)
result['evaluated_pose_seams'] = samples
(OUT / 'saved_surface_inspection.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result), flush=True)
