# MuMain Map Editor

A standalone Python desktop tool for editing MuMain client map data under Data/WorldN, with an exact 3D preview rendered by the client. It does not connect to a game server. Its Exact 3D preview starts the client renderer directly in an offline world scene.

## Start

Run from the repository root:

    python tools/map_editor/app.py

Open an EncTerrainN.map file from a client root Data/WorldN folder. The matching EncTerrainN.att, EncTerrainN.obj, and TerrainHeight.OZB files load when present.

## Views and editing

- **2D view:** inspect the full 256×256 map and paint mapping, attributes, or height.
- **Exact 3D preview:** opens a separate renderer window using the game renderer for terrain geometry, texture layers, lighting, water, BMD models, and environmental effects. After normal client asset initialization, the world loads without opening a login connection. Use Refresh 3D after saving from Python to reload the map. The preview starts at ground level. Use WASD or the arrow keys to walk, hold the right mouse button to look, and hold Shift to run. Movement follows terrain height and stops at blocked or no-ground tiles. Enable “Click map to move 3D camera” in the Python editor to teleport by clicking a map tile; the red crosshair tracks the live camera position on the 2D map. If the renderer does not acknowledge the command or publish its position, the editor reports that the client needs to be rebuilt from the latest source. This is useful for inspecting water, blocked regions, and the map edges.
- **Textures:** paint either mapping layer. Painting Layer 2 sets its alpha to opaque; right-click clears that overlay.
- **Attributes:** paint Walkable (0), Safezone (1), Blocked (4), No ground (8), or Water (16). Right-click paints Walkable.
- **Height:** left drag raises and right drag lowers the height brush. Stored values stay within the native 0–255 range.
- **Objects:** the table edits type, world position, rotation, and scale. Refresh the 3D preview after saving to inspect changed models in the game renderer.
- **Undo:** Ctrl+Z restores the previous terrain painting stroke in the Python editor.
- **Save:** Ctrl+S saves the current tab native file. Before the first overwrite in a session, the editor keeps a .bak copy beside the source.

## Renderer build

The exact preview requires a client rebuilt from this repository with CMake ENABLE_EDITOR enabled. The app looks for Main.exe under out/build/windows-x64-vs2022/src or out/build/windows-x64-mueditor/src and otherwise asks you to select it. It passes the selected client root as --data-root, so map and model resources come from that root while bundled fonts/config stay beside the executable.

## New maps

Choose New map…, select a source WorldN folder and the target Data folder, then choose an unused world number. The editor creates blank EncTerrainN.map, .att, .obj, and TerrainHeight.OZB files, and copies the source world terrain textures. If the corresponding ObjectN folder does not exist, it also copies the source object models. It does not register the new world in client C++ or server configuration.

## Client and server attributes

Save client attributes with Save client .att. For a server export, first load the current server TerrainData downloaded from the OpenMU Admin Panel, then choose Export merged server .att. The export starts from the server file and replaces only tiles edited in this session that differ from the loaded client baseline. Upload only this merged server file to the Admin Panel Terrain Data field; do not upload the encrypted client EncTerrainN.att. The server map Number defaults to WorldN minus one and may be wrong for remapped worlds.
