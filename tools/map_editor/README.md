# MuMain Map Editor

A standalone Python desktop tool for viewing and editing MuMain client map data under Data/WorldN. It does not start the game.

## Start

Run from the repository root:

    python tools/map_editor/app.py

The editor uses Tkinter and Pillow. Open an EncTerrainN.map file from the map Data/WorldN folder. Related EncTerrainN.att, EncTerrainN.obj, and TerrainHeight.OZB files are loaded from that folder when present.

## Views and editing

- **2D view:** inspect the full 256×256 map and paint mapping, attributes, or height.
- **3D view:** orbit with the middle mouse button, zoom with the wheel, and paint the selected terrain mode on the perspective terrain.
- **Textures:** paint either mapping layer. Painting Layer 2 sets its alpha to opaque; right-click clears that overlay. The 3D view colors each terrain patch from the average color of its selected texture.
- **Attributes:** paint Walkable (0), Safezone (1), Blocked (4), No ground (8), or Water (16). Right-click paints Walkable.
- **Height:** left drag raises and right drag lowers the height brush. Stored values stay within the native 0–255 range.
- **Objects:** the table edits type, world position, rotation, and scale. In 3D view, click ground to place the selected object type, or drag an object marker to move it. BMD meshes are drawn with flat colors sampled from their material textures; this lightweight preview is not the game full textured renderer.
- **Undo:** Ctrl+Z restores the previous terrain painting stroke.
- **Save:** Ctrl+S saves the current tab native file. Before the first overwrite in a session, the editor keeps a .bak copy beside the source.

## New maps

Choose New map…, select a source WorldN folder and the target Data folder, then choose an unused world number. The editor creates blank EncTerrainN.map, .att, .obj, and TerrainHeight.OZB files, and copies the source world terrain textures. If the corresponding ObjectN folder does not exist, it also copies the source object models. It does not register the new world in client C++ or server configuration; game integration still needs to be configured separately.

## Client and server attributes

Save client attributes with Save client .att. For a server export, first load the current server TerrainData downloaded from the OpenMU Admin Panel, then choose Export merged server .att. The export starts from the server file and replaces only tiles edited in this session that differ from the loaded client baseline. Upload only this merged server file to the Admin Panel Terrain Data field; do not upload the encrypted client EncTerrainN.att. The server map Number defaults to WorldN minus one and may be wrong for remapped worlds.
