---
name: mu-art-pipeline
description: Use when inspecting, creating, importing, exporting, or editing 3D models and textures for the MuMain MU Online client with this repository's Python and Blender MCP tools.
---

# MuMain game art workflow

Use the repository's Python and MCP tools for repeatable asset work. Keep source assets under src/bin/Data read-only during preparation; stage inputs and write generated files under tools/art_pipeline/workspace. Workflow documentation and operator scripts are grouped under this Skill; the installable Python package is in scripts/mu_art_pipeline.

## Choose the workflow

- For asset discovery, use mu_art_pipeline list_game_assets and inspect_texture. Stage a source with stage_asset before conversion or editing.
- For OZJ/OZT textures, use convert_workspace_texture to decode to JPEG/TGA. For raster image generation or edits, use the imagegen skill when available, then put the result in the workspace, load it onto the Blender material with load_texture when model export needs it, and convert it back with the project tool. Preserve dimensions, alpha, and the original filename when compatibility depends on them. The client limit is 1024x1024.
- For an existing MU BMD, stage it and use mu_blender import_bmd. This reads client BMD v10/v12, creates a weighted Blender armature, and creates one Blender Action per BMD action. The imported mesh is posed at the first frame. Exporting an imported model writes edited geometry with its source skeleton and original BMD action records; Blender Action edits are not encoded into the BMD animation data.
- For a new model or a model to bake to one game pose, use Blender MCP scene tools to create or edit mesh objects, materials, and transforms. Set the intended scene frame, select the mesh objects, then use export_bmd for a game-format v12 BMD. The exporter applies object transforms and modifiers, groups by material, and writes connected material images as OZT files in a sibling texture folder.
- To place a prepared model in the client data, preview it with mu-art install <workspace-relative-bmd> --target <Data-relative-path> --dry-run, then install it with the same command without --dry-run. Existing destinations require --overwrite; replaced files are backed up under tools/art_pipeline/workspace/backups. The installer validates the BMD and bundled OZT/OZJ textures. It reports texture names that are referenced but not included in the export bundle.
- Use import_model/export_model for OBJ, FBX, glTF, or GLB interchange, and save_blend to preserve an editable Blender project. Those interchange formats are not directly loaded by this client.

## Verify and hand off

- Run .agents/skills/mu-art-pipeline/scripts/run.ps1 mu-art model inspect <workspace-bmd-path> to validate a generated BMD and summarize meshes, textures, bones, and actions. This proves file structure only; it does not prove in-game appearance or compatibility.
- Reopen generated textures and inspect the model in Blender. For a game compatibility claim, test with the target client build and resource location.
- Keep generated BMD and texture files in the workspace until they have been reviewed. Do not overwrite or copy over src/bin/Data originals as part of preparation; when the user requests installation into game data, identify the exact destination and preserve a backup.

## Blender connection

The Blender Lab MCP add-on runs locally at 127.0.0.1:9876. If mu_blender tools cannot reach Blender, start D:\Blender\Start Blender MCP.cmd and check availability with blender_status before scene operations. Restart Codex after changing MCP configuration. The MCP entries and project commands must set UV_PROJECT_ENVIRONMENT to the repository-root .venv.

## Project references

- [Asset pipeline commands and model workflow](references/pipeline.md)
- [Blender and MCP setup](references/blender-mcp-setup.md)
- [Asset formats and repository locations](../../../docs/art-assets.md)
