---
name: mu-art-pipeline
description: Use when inspecting, creating, importing, exporting, or editing 3D models and textures for the MuMain MU Online client with this repository's Python and Blender MCP tools.
---

# MuMain game art workflow

Use the repository's Python and MCP tools for repeatable asset work. Keep source assets under src/bin/Data read-only during preparation; stage inputs and write generated files under tools/art_pipeline/workspace. Workflow documentation and operator scripts are grouped under this Skill; the installable Python package is in scripts/mu_art_pipeline.

## Character recovery default

The user approved the client-style Dark Wizard group and requested this structure for future character recovery: independent body meshes bound to one shared Player armature, preserving the source actions, UVs, textures, and node assignments. Do not Join, weld, or bake the character into one static mesh by default. Start from original BMD/OZJ resources; existing Corrected/OBJ/Blend geometry is not recovery input.

For the initial Dark Wizard, run `scripts/create_dark_wizard_group.py` with the repository-root `.venv` and a new workspace output directory. It creates five independent Class01 meshes on one 60-bone Player armature with all 284 source actions; initially only action 1/key 0 is active. Read [Character recovery and textures](references/character-model-assembly-and-textures.md) for the complete creation steps, reusable modules, controls, and deferred lighting issue. Other characters require their actual client body-slot mapping.

Use [historical static tools](references/dark-wizard-static-history.md) only when the user explicitly requests a static snapshot or merged output. The legacy OBJ rebuild command requires `--static-snapshot`.

## Player action lookup

For the meaning of an animation index or a `PLAYER_...` constant, read [Player action index: all 284 actions](references/player-action-index.md). It includes common-action lookup, categories, the complete enum-to-BMD table, key counts, and the alias/conditional-macro rules. Names are extracted from `_enum.h`; Chinese descriptions are readable glosses. This is the shared Player set, including other classes and mounted variants.

Refresh after source changes with the root `.venv`: `scripts/extract_player_actions.py --update-skill`. The extractor matches enum profiles to the BMD action count and refuses ambiguous matches. An imported Blender action's `mu_bmd_action_index` is the lookup key; only the active action is visible at a time.

## Choose the workflow

- For asset discovery, use mu_art_pipeline list_game_assets and inspect_texture. Stage a source with stage_asset before conversion or editing.
- For OZJ/OZT textures, use convert_workspace_texture to decode to JPEG/TGA. For raster image generation or edits, use the imagegen skill when available, then put the result in the workspace, load it onto the Blender material with load_texture when model export needs it, and convert it back with the project tool. Preserve dimensions, alpha, and the original filename when compatibility depends on them. The client limit is 1024x1024.
- For a standalone MU BMD, stage it and use mu_blender import_bmd. This reads client BMD v10/v12, creates a weighted Blender armature, and creates one Blender Action per BMD action. The imported mesh is posed at the first frame. Exporting an imported model writes edited geometry with its source skeleton and original BMD action records; Blender Action edits are not encoded into the BMD animation data.
- For player body-part textures that appear on the wrong body regions, read [Character recovery and texture alignment](references/character-model-assembly-and-textures.md). BMD import converts UVs to `(U, 1 - V)` and export converts back; keep decoded images upright and avoid a second flip.
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
