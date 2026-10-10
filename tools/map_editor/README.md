# MuMain Map Editor

A standalone 2D desktop tool for inspecting and editing client map data under Data/WorldN. It does not start the game.

## Start

Run from the repository root:

    python tools/map_editor/app.py

The project Python environment already includes Pillow. The editor opens an EncTerrainN.map file; choose the matching file inside the map's Data/WorldN folder. Related EncTerrainN.att, EncTerrainN.obj, and TerrainHeight.OZB files are loaded from that folder when present.

## Editing

- Texture: paint either mapping layer. Painting Layer 2 sets its alpha to opaque; right-click clears that overlay.
- Attribute: paint Walkable (0), Safezone (1), Blocked (4), No ground (8), or Water (16). Right-click paints Walkable.
- Height: left drag raises and right drag lowers the height brush. The canvas shows the stored 0–255 height values; values stay within the native OZB range.
- Objects: double-click a table value to edit type, world position, rotation, or scale. Add inserts an object at the map centre; Delete removes the selected row. The editor shows object positions as points and does not render BMD models.
- Undo: Ctrl+Z restores the previous terrain painting stroke.
- Save: Ctrl+S saves the current tab's native file. Before the first overwrite in a session, the editor keeps a .bak copy beside the source.

## Client and server attributes

Save client attributes with Save client .att. For a server export, first load the current server TerrainData downloaded from the OpenMU Admin Panel, then choose Export merged server .att. The export starts from the server file and replaces only tiles edited in this session that differ from the loaded client baseline. Upload only this merged server file to the Admin Panel's Terrain Data field; do not upload the encrypted client EncTerrainN.att. Set the server map Number field to the Admin Panel world enum; it defaults to WorldN minus one and can be wrong for remapped special worlds. Client World folder numbers and server map enum numbers can differ.

The map canvas uses average colors from the map's terrain textures for a compact overview. It shows mapping indices and attribute/height overlays, not the game's full 3D terrain rendering.
