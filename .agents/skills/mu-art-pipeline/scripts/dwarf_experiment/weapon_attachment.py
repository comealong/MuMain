"""Normal hand-held Sword01: RenderLinkObject(Link=false), not the back-item branch."""
import numpy as np
from mu_art_pipeline.poses import pose_matrices

RIGHT_WEAPON_NODE = 33
RIGHT_WEAPON_NAME = 'knife_gdf'
WEAPON_ACTION = 0
WEAPON_KEY = 0
ATTACHMENT_MODE = 'client_held_Link_false'


def runtime_matrices(model, action, key):
    matrices = np.array(pose_matrices(model, action, key))
    if model['actions'][action]['lock_positions']:
        root = model['bones'][0]['actions'][action]['positions']
        offset = np.array(root[key][:2]) - root[0][:2]
        for index, bone in enumerate(model['bones']):
            if not bone['dummy']:
                matrices[index, :2, 3] -= offset
    return matrices


def validate_sword_socket(player, weapon):
    bone = player['bones'][RIGHT_WEAPON_NODE]
    if bone['dummy'] or bone['name'] != RIGHT_WEAPON_NAME:
        raise ValueError('Player right-hand weapon socket does not match the client')
    if len(weapon['meshes']) != 1 or weapon['actions'][WEAPON_ACTION]['keys'] != 1:
        raise ValueError('Rigid Sword01 preview requires one mesh and one action-0 key')


def client_held_weapon_vertices(player, weapon, action, key, origin, scale):
    """Evaluate BMD Animation parent composition and SkinVertex at actor scale 1.

    Link=false supplies the socket directly as ParentMatrix. Optional weapon
    size is applied uniformly after the item pose, around the socket origin.
    """
    socket = runtime_matrices(player, action, key)[RIGHT_WEAPON_NODE]
    item_bones = runtime_matrices(weapon, WEAPON_ACTION, WEAPON_KEY)
    points = []
    for vertex in weapon['meshes'][0]['vertices']:
        attached = socket @ item_bones[vertex['node']]
        item_point = np.append(vertex['position'], 1.0)
        point = (attached @ item_point)[:3]
        point = socket[:3, 3] + scale * (point - socket[:3, 3])
        points.append(point + np.array(origin))
    return np.array(points)
