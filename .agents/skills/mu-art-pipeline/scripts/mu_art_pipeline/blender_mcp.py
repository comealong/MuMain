"""MCP tools for working with Blender through the Blender Lab add-on."""

from __future__ import annotations

import json
import math
import uuid
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .blender_client import BlenderConnectionError, execute_blender
from .bmd import encode_bmd_v12, encode_static_bmd_v12, parse_bmd
from .inventory import find_repository_root
from .textures import convert_texture


server = FastMCP("MuMain Blender")
SUPPORTED_IMPORTS = {".fbx", ".glb", ".gltf", ".obj"}
SUPPORTED_EXPORTS = {".fbx", ".glb", ".gltf", ".obj"}
PRIMITIVE_OPERATORS = {
    "cube": ("bpy.ops.mesh.primitive_cube_add", "size"),
    "cone": ("bpy.ops.mesh.primitive_cone_add", "radius1"),
    "cylinder": ("bpy.ops.mesh.primitive_cylinder_add", "radius"),
    "plane": ("bpy.ops.mesh.primitive_plane_add", "size"),
    "sphere": ("bpy.ops.mesh.primitive_uv_sphere_add", "radius"),
    "torus": ("bpy.ops.mesh.primitive_torus_add", "major_radius"),
}


def _workspace() -> Path:
    workspace = find_repository_root() / "tools" / "art_pipeline" / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace.resolve()


def _workspace_path(relative_path: str, allowed_extensions: set[str]) -> Path:
    workspace = _workspace()
    candidate = (workspace / relative_path).resolve()
    if not candidate.is_relative_to(workspace):
        raise ValueError("Files must stay inside tools/art_pipeline/workspace.")
    if candidate.suffix.lower() not in allowed_extensions:
        choices = ", ".join(sorted(allowed_extensions))
        raise ValueError(f"Unsupported file extension. Allowed: {choices}.")
    return candidate


def _vector3(value: list[float], argument_name: str) -> tuple[float, float, float]:
    if len(value) != 3 or not all(math.isfinite(float(axis)) for axis in value):
        raise ValueError(f"{argument_name} must contain three finite numbers.")
    return tuple(float(axis) for axis in value)


@server.tool()
def blender_status() -> dict[str, object]:
    """Check whether Blender is open and the official MCP add-on is responding."""
    return execute_blender(
        "import bpy\n"
        "result = {\n"
        "    'version': bpy.app.version_string,\n"
        "    'scene': bpy.context.scene.name,\n"
        "    'object_count': len(bpy.data.objects),\n"
        "}\n"
    )


@server.tool()
def get_scene_info() -> dict[str, object]:
    """List objects in the open Blender scene with type and basic transforms."""
    return execute_blender(
        "import bpy\n"
        "objects = []\n"
        "for obj in bpy.context.scene.objects:\n"
        "    item = {\n"
        "        'name': obj.name,\n"
        "        'type': obj.type,\n"
        "        'location': [round(float(v), 4) for v in obj.location],\n"
        "        'dimensions': [round(float(v), 4) for v in obj.dimensions],\n"
        "    }\n"
        "    if obj.type == 'MESH':\n"
        "        polygons = list(obj.data.polygons)\n"
        "        item['vertices'] = len(obj.data.vertices)\n"
        "        item['polygons'] = len(polygons)\n"
        "        item['triangles'] = sum(max(0, len(polygon.vertices) - 2) for polygon in polygons)\n"
        "        item['quads'] = sum(len(polygon.vertices) == 4 for polygon in polygons)\n"
        "    objects.append(item)\n"
        "result = {'scene': bpy.context.scene.name, 'objects': objects}\n"
    )


@server.tool()
def create_primitive(
    primitive: str,
    name: str = "",
    location: list[float] | None = None,
    size: float = 1.0,
) -> dict[str, object]:
    """Create a Blender primitive mesh. Supported types: cube, cone, cylinder, plane, sphere, torus."""
    operator = PRIMITIVE_OPERATORS.get(primitive.lower())
    if operator is None:
        raise ValueError(f"primitive must be one of: {', '.join(sorted(PRIMITIVE_OPERATORS))}.")
    if not math.isfinite(size) or size <= 0 or size > 10000:
        raise ValueError("size must be finite and in the range (0, 10000].")
    position = _vector3(location or [0, 0, 0], "location")
    operator_name, size_argument = operator
    code = (
        "import bpy\n"
        f"{operator_name}({size_argument}={float(size)!r}, location={position!r})\n"
        f"obj = bpy.context.active_object\n"
        f"obj.name = {name[:64]!r} if {bool(name)!r} else obj.name\n"
        "result = {'name': obj.name, 'type': obj.type, "
        "'location': [float(v) for v in obj.location]}\n"
    )
    return execute_blender(code)


@server.tool()
def import_bmd(relative_path: str) -> dict[str, object]:
    """Import a staged MU Online BMD with a Blender armature and animation actions."""
    source = _workspace_path(relative_path, {".bmd"})
    model = parse_bmd(source)
    model["source_name"] = model["name"]
    model["name"] = source.stem
    model_json = json.dumps(model, ensure_ascii=True, separators=(",", ":"))
    script_lines = [
        "import bpy, json",
        "from mathutils import Euler, Matrix, Vector",
        f"model = json.loads({model_json!r})",
        "def bone_matrix(index, action_index=0, key_index=0, visiting=None):",
        "    if visiting is None: visiting = set()",
        "    if index in visiting: raise ValueError('BMD bone hierarchy contains a cycle')",
        "    visiting.add(index)",
        "    bone = model['bones'][index]",
        "    if bone['dummy']:",
        "        local = Matrix.Identity(4)",
        "    else:",
        "        actions = bone['actions']",
        "        action = actions[action_index] if action_index < len(actions) else {}",
        "        positions = action.get('positions', [])",
        "        rotations = action.get('rotations', [])",
        "        position = positions[key_index] if key_index < len(positions) else [0.0, 0.0, 0.0]",
        "        rotation = rotations[key_index] if key_index < len(rotations) else [0.0, 0.0, 0.0]",
        "        local = Matrix.Translation(Vector(position)) @ Euler(rotation, 'XYZ').to_matrix().to_4x4()",
        "    parent = bone['parent']",
        "    result = bone_matrix(parent, action_index, key_index, visiting) @ local if parent >= 0 else local",
        "    visiting.remove(index)",
        "    return result",
        "bone_count = len(model['bones'])",
        "action_count = len(model['actions'])",
        "rest_matrices = [bone_matrix(i, 0, 0) for i in range(bone_count)] if bone_count else []",
        "created = []",
        "rig = None",
        "if bone_count:",
        "    armature_data = bpy.data.armatures.new(model['name'] + '_Armature')",
        "    rig = bpy.data.objects.new(model['name'] + '_Armature', armature_data)",
        "    bpy.context.collection.objects.link(rig)",
        "    rig['mu_bmd_source'] = model['source_name']",
        "    rig['mu_bmd_version'] = model['version']",
        "    rig['mu_bmd_action_count'] = action_count",
        "    source_meta = {'name': model['source_name'], 'bones': model['bones'], 'actions': model['actions'], 'blender_bone_names': [], 'blender_action_names': []}",
        "    source_meta['rest_matrices'] = [[[float(value) for value in row] for row in matrix] for matrix in rest_matrices]",
        "    bpy.ops.object.select_all(action='DESELECT')",
        "    bpy.context.view_layer.objects.active = rig",
        "    rig.select_set(True)",
        "    bpy.ops.object.mode_set(mode='EDIT')",
        "    edit_bones = []",
        "    for bone_index, bone_record in enumerate(model['bones']):",
        "        edit_bone = armature_data.edit_bones.new(bone_record['name'][:60] or 'bone_' + str(bone_index))",
        "        edit_bone.matrix = rest_matrices[bone_index]",
        "        edit_bone.length = max(float(edit_bone.length), 0.1)",
        "        edit_bones.append(edit_bone)",
        "    for bone_index, bone_record in enumerate(model['bones']):",
        "        parent_index = bone_record['parent']",
        "        if parent_index >= 0:",
        "            edit_bones[bone_index].parent = edit_bones[parent_index]",
        "            edit_bones[bone_index].use_connect = False",
        "    bone_names = [bone.name for bone in edit_bones]",
        "    source_meta['blender_bone_names'] = bone_names",
        "    bpy.ops.object.mode_set(mode='OBJECT')",
        "    rig.animation_data_create()",
        "    scene = bpy.context.scene",
        "    first_action = None",
        "    for action_index, action_record in enumerate(model['actions']):",
        "        action_name = model['name'] + '_Action_' + format(action_index, '02d')",
        "        action = bpy.data.actions.new(action_name)",
        "        action.use_fake_user = True",
        "        rig.animation_data.action = action",
        "        if action_index == 0: first_action = action",
        "        source_meta['blender_action_names'].append(action.name)",
        "        key_count = max(action_record['keys'], 1)",
        "        for key_index in range(key_count):",
        "            scene.frame_set(key_index + 1)",
        "            matrices = [bone_matrix(i, action_index, key_index) for i in range(bone_count)]",
        "            for bone_index, bone_name in enumerate(bone_names):",
        "                pose_bone = rig.pose.bones[bone_name]",
        "                pose_bone.rotation_mode = 'XYZ'",
        "                pose_bone.matrix = matrices[bone_index]",
        "            bpy.context.view_layer.update()",
        "            for bone_name in bone_names:",
        "                pose_bone = rig.pose.bones[bone_name]",
        "                pose_bone.keyframe_insert(data_path='location', frame=key_index + 1, group=bone_name)",
        "                pose_bone.keyframe_insert(data_path='rotation_euler', frame=key_index + 1, group=bone_name)",
        "                pose_bone.keyframe_insert(data_path='scale', frame=key_index + 1, group=bone_name)",
        "    source_text = bpy.data.texts.new(model['name'] + '_BMD_Source')",
        "    source_text.write(json.dumps(source_meta, separators=(',', ':')))",
        "    rig['mu_bmd_source_text'] = source_text.name",
        "    if action_count:",
        "        rig.animation_data.action = first_action",
        "        scene.frame_set(1)",
        "for mesh_index, item in enumerate(model['meshes']):",
        "    vertices = []",
        "    node_indices = []",
        "    for vertex in item['vertices']:",
        "        point = Vector(vertex['position'])",
        "        node = vertex['node']",
        "        node_indices.append(node)",
        "        vertices.append(tuple(rest_matrices[node] @ point) if rest_matrices and 0 <= node < bone_count else tuple(point))",
        "    faces = [triangle['vertices'] for triangle in item['triangles']]",
        "    mesh_name = model['name'] + '_mesh_' + format(mesh_index, '02d')",
        "    mesh = bpy.data.meshes.new(mesh_name)",
        "    mesh.from_pydata(vertices, [], faces)",
        "    mesh.update()",
        "    source_position_attribute = mesh.attributes.new(name='mu_bmd_source_position', type='FLOAT_VECTOR', domain='POINT')",
        "    source_node_attribute = mesh.attributes.new(name='mu_bmd_source_node', type='INT', domain='POINT')",
        "    source_base_attribute = mesh.attributes.new(name='mu_bmd_base_position', type='FLOAT_VECTOR', domain='POINT')",
        "    for vertex_index, vertex_record in enumerate(item['vertices']):",
        "        source_position_attribute.data[vertex_index].vector = vertex_record['position']",
        "        source_node_attribute.data[vertex_index].value = vertex_record['node']",
        "        source_base_attribute.data[vertex_index].vector = vertices[vertex_index]",
        "    if mesh.polygons:",
        "        uv_layer = mesh.uv_layers.new(name='UVMap') if item['uvs'] else None",
        "        loop_normals = []",
        "        source_normals = []",
        "        source_normal_nodes = []",
        "        for polygon, triangle in zip(mesh.polygons, item['triangles']):",
        "            for corner, loop_index in enumerate(polygon.loop_indices):",
        "                if uv_layer:",
        "                    u, v = item['uvs'][triangle['uvs'][corner]]",
        "                    # Client image rows start at the top; Blender UVs start at the bottom.",
        "                    uv_layer.data[loop_index].uv = (u, 1.0 - v)",
        "                normal_record = item['normals'][triangle['normals'][corner]]",
        "                source_normals.append(normal_record['normal'])",
        "                source_normal_nodes.append(normal_record['node'])",
        "                normal = Vector(normal_record['normal'])",
        "                node = normal_record['node']",
        "                if rest_matrices and 0 <= node < bone_count: normal = rest_matrices[node].to_3x3() @ normal",
        "                if normal.length_squared: loop_normals.append(tuple(normal.normalized()))",
        "                else: loop_normals.append((0.0, 0.0, 1.0))",
        "        try: mesh.normals_split_custom_set(loop_normals)",
        "        except (AttributeError, RuntimeError): pass",
        "        source_normal_attribute = mesh.attributes.new(name='mu_bmd_source_normal', type='FLOAT_VECTOR', domain='CORNER')",
        "        source_normal_node_attribute = mesh.attributes.new(name='mu_bmd_source_normal_node', type='INT', domain='CORNER')",
        "        for loop_index, source_normal in enumerate(source_normals):",
        "            source_normal_attribute.data[loop_index].vector = source_normal",
        "            source_normal_node_attribute.data[loop_index].value = source_normal_nodes[loop_index]",
        "    obj = bpy.data.objects.new(mesh_name, mesh)",
        "    bpy.context.collection.objects.link(obj)",
        "    if rig:",
        "        mesh_groups = [obj.vertex_groups.new(name=bone.name) for bone in rig.data.bones]",
        "        for node in range(bone_count):",
        "            indices = [i for i, vertex_node in enumerate(node_indices) if vertex_node == node]",
        "            if indices: mesh_groups[node].add(indices, 1.0, 'REPLACE')",
        "        modifier = obj.modifiers.new('BMD Armature', 'ARMATURE')",
        "        modifier.object = rig",
        "    texture = item['texture']",
        "    if texture:",
        "        material = bpy.data.materials.new(texture)",
        "        material['mu_bmd_texture_file'] = texture",
        "        obj.data.materials.append(material)",
        "    obj['mu_bmd_source'] = model['source_name']",
        "    obj['mu_bmd_version'] = model['version']",
        "    obj['mu_bmd_mesh_index'] = mesh_index",
        "    obj['mu_bmd_uv_convention'] = 'blender_bottom_left'",
        "    created.append(obj.name)",
        "bpy.ops.object.select_all(action='DESELECT')",
        "for obj in bpy.data.objects:",
        "    if obj.name in created or (rig and obj == rig): obj.select_set(True)",
        "if created: bpy.context.view_layer.objects.active = bpy.data.objects[created[-1]]",
        "result = {'imported': True, 'model': model['name'], 'version': model['version'], 'objects': created, 'rig': rig.name if rig else None, 'bones': bone_count, 'animations': action_count, 'pose': 'action_0_frame_0'}",
    ]
    return execute_blender("\n".join(script_lines) + "\n")


@server.tool()
def export_bmd(relative_path: str, overwrite: bool = False) -> dict[str, object]:
    """Export selected Blender meshes as v12 BMD; imported rigs retain source action data."""
    destination = _workspace_path(relative_path, {".bmd"})
    if destination.exists() and not overwrite:
        raise FileExistsError(f"BMD already exists; set overwrite=true to replace: {relative_path}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    texture_directory = destination.parent / (destination.stem + "_textures")
    if texture_directory.exists() and any(texture_directory.iterdir()) and not overwrite:
        raise FileExistsError(f"BMD texture output directory is not empty: {texture_directory}")
    texture_directory.mkdir(parents=True, exist_ok=True)
    payload_path = destination.parent / f".{destination.stem}_{uuid.uuid4().hex}.json"
    scene_script = _build_bmd_scene_export(destination.stem, texture_directory, payload_path)
    exported = execute_blender(scene_script)
    if exported.get("error"):
        raise ValueError(str(exported["error"]))
    reported_path = Path(str(exported.get("payload_path", ""))).resolve()
    if reported_path != payload_path.resolve() or not reported_path.is_relative_to(_workspace()):
        raise ValueError("Blender returned an invalid BMD payload path.")
    try:
        scene_data = json.loads(reported_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("Blender returned invalid BMD scene data.") from error
    finally:
        reported_path.unlink(missing_ok=True)

    from PIL import Image

    scene_textures = scene_data.pop("textures", [])
    for texture in scene_textures:
        png_path = Path(texture["png"]).resolve()
        if not png_path.is_relative_to(_workspace()):
            raise ValueError("Exported texture escaped the art-pipeline workspace.")
        tga_path = png_path.with_suffix(".tga")
        ozt_path = png_path.with_suffix(".ozt")
        with Image.open(png_path) as image:
            image.convert("RGBA").save(tga_path, format="TGA")
        convert_texture(tga_path, ozt_path, overwrite=overwrite)
        png_path.unlink(missing_ok=True)

    skeleton = scene_data.pop("skeleton", None)
    if skeleton:
        output_bytes = encode_bmd_v12(destination.stem, scene_data["meshes"], skeleton["bones"], skeleton["actions"])
    else:
        output_bytes = encode_static_bmd_v12(destination.stem, scene_data["meshes"])
    destination.write_bytes(output_bytes)
    return {
        "exported": True,
        "file": destination.relative_to(_workspace()).as_posix(),
        "meshes": len(scene_data["meshes"]),
        "vertices": sum(len(mesh["vertices"]) for mesh in scene_data["meshes"]),
        "triangles": sum(len(mesh["triangles"]) for mesh in scene_data["meshes"]),
        "textures": len(scene_textures),
        "bones": len(skeleton["bones"]) if skeleton else 1,
        "actions": len(skeleton["actions"]) if skeleton else 1,
        "animation": "source actions preserved" if skeleton else "static pose",
        "format": "MU Online BMD v12",
    }


def _build_bmd_scene_export(model_name: str, texture_directory: Path, payload_path: Path) -> str:
    payload_path_json = json.dumps(str(payload_path))
    safe_stem = "".join(char if char.isalnum() or char in "_-" else "_" for char in model_name)[:20] or "model"
    texture_dir_json = json.dumps(str(texture_directory))
    safe_stem_json = json.dumps(safe_stem)
    return "\n".join([
        "import bpy, json, os",
        "from mathutils import Matrix, Vector",
        "objects = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']",
        "if not objects: raise ValueError('Select at least one mesh object before exporting.')",
        "rigs = []",
        "for obj in objects:",
        "    for modifier in obj.modifiers:",
        "        if modifier.type == 'ARMATURE' and modifier.object and modifier.object not in rigs: rigs.append(modifier.object)",
        "if len(rigs) > 1: raise ValueError('Selected meshes must use the same armature.')",
        "source_rig = rigs[0] if rigs else None",
        "source_text = bpy.data.texts.get(source_rig.get('mu_bmd_source_text', '')) if source_rig else None",
        "source_meta = json.loads(source_text.as_string()) if source_text else None",
        "armature_modifier_states = []",
        "if source_meta:",
        "    for obj in objects:",
        "        for modifier in obj.modifiers:",
        "            if modifier.type == 'ARMATURE' and modifier.object == source_rig:",
        "                armature_modifier_states.append((modifier, modifier.show_viewport))",
        "                modifier.show_viewport = False",
        "    bpy.context.view_layer.update()",
        "scene = bpy.context.scene",
        "previous_frame = scene.frame_current",
        "previous_action = source_rig.animation_data.action if source_rig and source_rig.animation_data else None",
        "pose_matrices = []",
        "if source_meta:",
        "    action_names = source_meta.get('blender_action_names', [])",
        "    source_action = bpy.data.actions.get(action_names[0]) if action_names else None",
        "    if source_action is None: raise ValueError('The source BMD first action is missing from this Blender file.')",
        "    source_rig.animation_data.action = source_action",
        "    scene.frame_set(1)",
        "    bpy.context.view_layer.update()",
        "    pose_matrices = [source_rig.pose.bones[name].matrix.copy() for name in source_meta['blender_bone_names']]",
        f"texture_dir = {texture_dir_json}",
        "os.makedirs(texture_dir, exist_ok=True)",
        "payload = {'meshes': [], 'textures': []}",
        "if source_meta: payload['skeleton'] = {'bones': source_meta['bones'], 'actions': source_meta['actions']}",
        "bone_indices = {name: index for index, name in enumerate(source_meta['blender_bone_names'])} if source_meta else {}",
        "seen_images = {}",
        "depsgraph = bpy.context.evaluated_depsgraph_get()",
        "for obj in objects:",
        "    evaluated = obj.evaluated_get(depsgraph)",
        "    mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)",
        "    try:",
        "        mesh.calc_loop_triangles()",
        "        grouped = {}",
        "        for triangle in mesh.loop_triangles:",
        "            slot = mesh.polygons[triangle.polygon_index].material_index",
        "            grouped.setdefault(slot, []).append(triangle)",
        "        if not grouped: grouped[0] = []",
        "        group_nodes = {}",
        "        if source_meta:",
        "            for group in obj.vertex_groups:",
        "                if group.name in bone_indices: group_nodes[group.index] = bone_indices[group.name]",
        "        for slot, source_triangles in grouped.items():",
        "            material = obj.material_slots[slot].material if slot < len(obj.material_slots) else None",
        "            image = next((node.image for node in material.node_tree.nodes if node.type == 'TEX_IMAGE' and node.image), None) if material and material.use_nodes else None",
        "            texture_name = ''",
        "            if image:",
        "                image_key = image.name_full",
        "                if image_key not in seen_images:",
        f"                    png_path = os.path.join(texture_dir, {safe_stem_json} + '_tex_' + format(len(seen_images), '02d') + '.png')",
        "                    image.save(filepath=png_path)",
        "                    texture_name = os.path.basename(png_path)[:-4] + '.ozt'",
        "                    seen_images[image_key] = (png_path, texture_name)",
        "                    payload['textures'].append({'png': png_path})",
        "                else: texture_name = seen_images[image_key][1]",
        "            elif material and material.get('mu_bmd_texture_file'): texture_name = os.path.basename(material['mu_bmd_texture_file'])[:31]",
        "            record = {'texture': texture_name, 'texture_index': 0, 'vertices': [], 'normals': [], 'uvs': [], 'triangles': []}",
        "            vertex_map, normal_map, uv_map = {}, {}, {}",
        "            uv_layer = mesh.uv_layers.active",
        "            source_position_attribute = mesh.attributes.get('mu_bmd_source_position') if source_meta else None",
        "            # Older imported rigs retain source UVs; preserve their existing export behavior.",
        "            legacy_source_uv = source_position_attribute is not None and obj.get('mu_bmd_uv_convention') is None",
        "            source_node_attribute = mesh.attributes.get('mu_bmd_source_node') if source_meta else None",
        "            source_base_attribute = mesh.attributes.get('mu_bmd_base_position') if source_meta else None",
        "            source_normal_attribute = mesh.attributes.get('mu_bmd_source_normal') if source_meta else None",
        "            source_normal_node_attribute = mesh.attributes.get('mu_bmd_source_normal_node') if source_meta else None",
        "            normal_matrix = obj.matrix_world.to_3x3().inverted().transposed()",
        "            for triangle in source_triangles:",
        "                vertex_indices, normal_indices, uv_indices = [], [], []",
        "                for loop_index in triangle.loops:",
        "                    loop = mesh.loops[loop_index]",
        "                    source_vertex = loop.vertex_index",
        "                    node = 0",
        "                    if source_meta:",
        "                        weights = [(assignment.weight, group_nodes[assignment.group]) for assignment in mesh.vertices[source_vertex].groups if assignment.group in group_nodes]",
        "                        if weights: node = max(weights)[1]",
        "                        elif source_node_attribute: node = source_node_attribute.data[source_vertex].value",
        "                    vertex_key = (source_vertex, node)",
        "                    vertex_index = vertex_map.get(vertex_key)",
        "                    if vertex_index is None:",
        "                        position = obj.matrix_world @ mesh.vertices[source_vertex].co",
        "                        if source_meta:",
        "                            armature_position = source_rig.matrix_world.inverted() @ position",
        "                            attributes_valid = source_position_attribute and source_node_attribute and source_base_attribute and node < len(source_meta.get('rest_matrices', []))",
        "                            if attributes_valid:",
        "                                original_node = source_node_attribute.data[source_vertex].value",
        "                                rest_matrix = Matrix(source_meta['rest_matrices'][node])",
        "                                if original_node == node:",
        "                                    original_position = Vector(source_position_attribute.data[source_vertex].vector)",
        "                                    base_position = Vector(source_base_attribute.data[source_vertex].vector)",
        "                                    position = original_position + rest_matrix.to_3x3().inverted() @ (armature_position - base_position)",
        "                                else: position = rest_matrix.inverted() @ armature_position",
        "                            else: position = pose_matrices[node].inverted() @ armature_position",
        "                        vertex_index = len(record['vertices'])",
        "                        vertex_map[vertex_key] = vertex_index",
        "                        record['vertices'].append({'node': node, 'position': [float(value) for value in position]})",
        "                    normal_node = node",
        "                    if source_normal_attribute and source_normal_node_attribute:",
        "                        normal = Vector(source_normal_attribute.data[loop_index].vector)",
        "                        normal_node = source_normal_node_attribute.data[loop_index].value",
        "                    else:",
        "                        normal = normal_matrix @ mesh.corner_normals[loop_index].vector",
        "                        if normal.length_squared: normal.normalize()",
        "                        if source_meta:",
        "                            normal_armature = source_rig.matrix_world.to_3x3().transposed() @ normal",
        "                            normal = pose_matrices[node].to_3x3().transposed() @ normal_armature",
        "                            if normal.length_squared: normal.normalize()",
        "                    normal_value = tuple(float(value) for value in normal)",
        "                    normal_key = (normal_node, normal_value)",
        "                    normal_index = normal_map.get(normal_key)",
        "                    if normal_index is None:",
        "                        normal_index = len(record['normals'])",
        "                        normal_map[normal_key] = normal_index",
        "                        record['normals'].append({'node': normal_node, 'normal': list(normal_value), 'bind_vertex': 0})",
        "                    uv = uv_layer.data[loop_index].uv if uv_layer else (0.0, 0.0)",
        "                    # Convert Blender image UVs back to client UVs at the BMD boundary.",
        "                    source_v = 1.0 - float(uv[1]) if uv_layer and not legacy_source_uv else float(uv[1])",
        "                    uv_value = (float(uv[0]), source_v)",
        "                    uv_index = uv_map.get(uv_value)",
        "                    if uv_index is None:",
        "                        uv_index = len(record['uvs'])",
        "                        uv_map[uv_value] = uv_index",
        "                        record['uvs'].append(list(uv_value))",
        "                    vertex_indices.append(vertex_index)",
        "                    normal_indices.append(normal_index)",
        "                    uv_indices.append(uv_index)",
        "                record['triangles'].append({'size': 3, 'vertices': vertex_indices, 'normals': normal_indices, 'uvs': uv_indices})",
        "            if record['triangles']: payload['meshes'].append(record)",
        "    finally: evaluated.to_mesh_clear()",
        "if source_meta:",
        "    for modifier, show_viewport in armature_modifier_states: modifier.show_viewport = show_viewport",
        "    source_rig.animation_data.action = previous_action",
        "    scene.frame_set(previous_frame)",
        "    bpy.context.view_layer.update()",
        f"with open({payload_path_json}, 'w', encoding='utf-8') as payload_file: json.dump(payload, payload_file, separators=(',', ':'))",
        f"result = {{'payload_path': {payload_path_json}}}",
    ]) + "\n"


@server.tool()
def import_model(relative_path: str) -> dict[str, object]:
    """Import an OBJ, FBX, glTF, or GLB from the art-pipeline workspace."""
    source = _workspace_path(relative_path, SUPPORTED_IMPORTS)
    if not source.is_file():
        raise FileNotFoundError(f"Interchange model not found: {relative_path}")
    filepath = json.dumps(str(source))
    operators = {
        ".fbx": f"bpy.ops.import_scene.fbx(filepath={filepath})",
        ".glb": f"bpy.ops.import_scene.gltf(filepath={filepath})",
        ".gltf": f"bpy.ops.import_scene.gltf(filepath={filepath})",
        ".obj": f"bpy.ops.wm.obj_import(filepath={filepath})",
    }
    code = (
        "import bpy\n"
        f"{operators[source.suffix.lower()]}\n"
        "result = {'imported': True, 'file': "
        f"{json.dumps(source.name)}, 'object_count': len(bpy.context.selected_objects)}}\n"
    )
    return execute_blender(code)


@server.tool()
def export_model(relative_path: str, overwrite: bool = False) -> dict[str, object]:
    """Export the current Blender selection as OBJ, FBX, glTF, or GLB inside the workspace."""
    destination = _workspace_path(relative_path, SUPPORTED_EXPORTS)
    if destination.exists() and not overwrite:
        raise FileExistsError(f"Export already exists; set overwrite=true to replace: {relative_path}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    filepath = json.dumps(str(destination))
    operators = {
        ".fbx": f"bpy.ops.export_scene.fbx(filepath={filepath}, use_selection=True)",
        ".glb": f"bpy.ops.export_scene.gltf(filepath={filepath}, export_format='GLB', use_selection=True)",
        ".gltf": f"bpy.ops.export_scene.gltf(filepath={filepath}, export_format='GLTF_SEPARATE', use_selection=True)",
        ".obj": f"bpy.ops.wm.obj_export(filepath={filepath}, export_selected_objects=True)",
    }
    code = (
        "import bpy\n"
        f"{operators[destination.suffix.lower()]}\n"
        f"result = {{'exported': True, 'file': {json.dumps(str(destination.relative_to(_workspace()).as_posix()))}}}\n"
    )
    return execute_blender(code)


@server.tool()
def save_blend(relative_path: str, overwrite: bool = False) -> dict[str, object]:
    """Save the current Blender scene as a .blend file inside the workspace."""
    destination = _workspace_path(relative_path, {".blend"})
    if destination.exists() and not overwrite:
        raise FileExistsError(f"Blend file already exists; set overwrite=true to replace: {relative_path}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    filepath = json.dumps(str(destination))
    code = (
        "import bpy\n"
        f"bpy.ops.wm.save_as_mainfile(filepath={filepath})\n"
        f"result = {{'saved': True, 'file': {json.dumps(str(destination.relative_to(_workspace()).as_posix()))}}}\n"
    )
    return execute_blender(code)


@server.tool()
def create_mesh(
    name: str,
    vertices: list[list[float]],
    faces: list[list[int]],
) -> dict[str, object]:
    """Create a mesh from vertex coordinates and polygon indices (up to 15,000 vertices)."""
    if not vertices or len(vertices) > 15000:
        raise ValueError("vertices must contain between 1 and 15,000 points.")
    if not faces or len(faces) > 30000:
        raise ValueError("faces must contain between 1 and 30,000 polygons.")

    validated_vertices = [_vector3(vertex, "vertex") for vertex in vertices]
    validated_faces: list[tuple[int, ...]] = []
    for face in faces:
        if len(face) < 3 or len(face) > 4:
            raise ValueError("Each polygon must contain three or four vertex indices.")
        if any(index < 0 or index >= len(validated_vertices) for index in face):
            raise ValueError("A polygon index is outside the vertices array.")
        validated_faces.append(tuple(face))

    mesh_name = name[:64] or "MuMainMesh"
    code = (
        "import bpy\n"
        f"vertices = {validated_vertices!r}\n"
        f"faces = {validated_faces!r}\n"
        f"mesh = bpy.data.meshes.new({mesh_name!r})\n"
        "mesh.from_pydata(vertices, [], faces)\n"
        "mesh.update()\n"
        f"obj = bpy.data.objects.new({mesh_name!r}, mesh)\n"
        "bpy.context.collection.objects.link(obj)\n"
        "bpy.context.view_layer.objects.active = obj\n"
        "obj.select_set(True)\n"
        "result = {'name': obj.name, 'vertices': len(mesh.vertices), 'polygons': len(mesh.polygons)}\n"
    )
    return execute_blender(code)


@server.tool()
def create_material(
    name: str,
    color_rgba: list[float] | None = None,
    roughness: float = 0.5,
    metallic: float = 0.0,
) -> dict[str, object]:
    """Create a Principled BSDF material with validated color and surface values."""
    color = color_rgba or [0.8, 0.8, 0.8, 1.0]
    if len(color) != 4 or any(not math.isfinite(float(value)) or not 0 <= value <= 1 for value in color):
        raise ValueError("color_rgba must contain four finite values between 0 and 1.")
    if not math.isfinite(roughness) or not 0 <= roughness <= 1:
        raise ValueError("roughness must be between 0 and 1.")
    if not math.isfinite(metallic) or not 0 <= metallic <= 1:
        raise ValueError("metallic must be between 0 and 1.")

    material_name = name[:64] or "MuMainMaterial"
    code = (
        "import bpy\n"
        f"material = bpy.data.materials.new({material_name!r})\n"
        "material.use_nodes = True\n"
        f"color = {tuple(float(value) for value in color)!r}\n"
        "material.diffuse_color = color\n"
        "shader = material.node_tree.nodes.get('Principled BSDF')\n"
        "shader.inputs['Base Color'].default_value = color\n"
        f"shader.inputs['Roughness'].default_value = {float(roughness)!r}\n"
        f"shader.inputs['Metallic'].default_value = {float(metallic)!r}\n"
        "result = {'name': material.name, 'color_rgba': list(color)}\n"
    )
    return execute_blender(code)


@server.tool()
def assign_material(object_name: str, material_name: str) -> dict[str, object]:
    """Assign an existing Blender material to a named object."""
    code = (
        "import bpy\n"
        f"obj = bpy.data.objects.get({object_name[:64]!r})\n"
        f"material = bpy.data.materials.get({material_name[:64]!r})\n"
        "if obj is None or material is None:\n"
        "    result = {'assigned': False, 'object_found': obj is not None, 'material_found': material is not None}\n"
        "else:\n"
        "    if obj.data and hasattr(obj.data, 'materials'):\n"
        "        if obj.data.materials:\n"
        "            obj.data.materials[0] = material\n"
        "        else:\n"
        "            obj.data.materials.append(material)\n"
        "    result = {'assigned': True, 'object': obj.name, 'material': material.name}\n"
    )
    return execute_blender(code)


@server.tool()
def load_texture(
    object_name: str,
    material_name: str,
    relative_path: str,
) -> dict[str, object]:
    """Load a workspace image and connect it to an object's material base color."""
    texture = _workspace_path(relative_path, {".bmp", ".jpeg", ".jpg", ".png", ".tga"})
    if not texture.is_file():
        raise FileNotFoundError(f"Texture not found in the art-pipeline workspace: {relative_path}")

    material_label = material_name[:64] or "MuMainMaterial"
    object_label = object_name[:64]
    texture_path = json.dumps(str(texture))
    code = (
        "import bpy\n"
        f"obj = bpy.data.objects.get({object_label!r})\n"
        "if obj is None:\n"
        "    result = {'loaded': False, 'error': 'Object not found'}\n"
        "else:\n"
        f"    image = bpy.data.images.load({texture_path}, check_existing=True)\n"
        f"    material = bpy.data.materials.get({material_label!r}) or bpy.data.materials.new({material_label!r})\n"
        "    material.use_nodes = True\n"
        "    shader = material.node_tree.nodes.get('Principled BSDF')\n"
        "    if shader is None:\n"
        "        shader = material.node_tree.nodes.new('ShaderNodeBsdfPrincipled')\n"
        "    image_node = material.node_tree.nodes.new('ShaderNodeTexImage')\n"
        "    image_node.image = image\n"
        "    material.node_tree.links.new(image_node.outputs['Color'], shader.inputs['Base Color'])\n"
        "    if obj.data and hasattr(obj.data, 'materials'):\n"
        "        if obj.data.materials:\n"
        "            obj.data.materials[0] = material\n"
        "        else:\n"
        "            obj.data.materials.append(material)\n"
        f"    result = {{'loaded': True, 'object': obj.name, 'material': material.name, 'image': image.name, 'file': {relative_path!r}}}\n"
    )
    return execute_blender(code)


@server.tool()
def set_transform(
    object_name: str,
    location: list[float] | None = None,
    rotation_radians: list[float] | None = None,
    scale: list[float] | None = None,
) -> dict[str, object]:
    """Set location, Euler rotation, or scale for a named Blender object."""
    if location is None and rotation_radians is None and scale is None:
        raise ValueError("Supply at least one of location, rotation_radians, or scale.")
    location_value = _vector3(location, "location") if location is not None else None
    rotation_value = _vector3(rotation_radians, "rotation_radians") if rotation_radians is not None else None
    scale_value = _vector3(scale, "scale") if scale is not None else None
    lines = [
        "import bpy",
        f"obj = bpy.data.objects.get({object_name[:64]!r})",
        "if obj is None:",
        "    result = {'error': 'Object not found'}",
        "else:",
    ]
    if location_value is not None:
        lines.append(f"    obj.location = {location_value!r}")
    if rotation_value is not None:
        lines.append(f"    obj.rotation_euler = {rotation_value!r}")
    if scale_value is not None:
        lines.append(f"    obj.scale = {scale_value!r}")
    lines.append("    result = {'name': obj.name, 'location': list(obj.location), 'rotation': list(obj.rotation_euler), 'scale': list(obj.scale)}")
    return execute_blender("\n".join(lines) + "\n")


def main() -> None:
    server.run(transport="stdio")
