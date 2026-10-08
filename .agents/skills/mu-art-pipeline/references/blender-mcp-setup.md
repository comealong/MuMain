# Blender MCP setup for MuMain

The workflow uses Blender for authoring, a local MCP connection for scene operations, and the project's Python tools for client asset discovery and validation. Keep source game assets read-only and use copies in tools/art_pipeline/workspace.

## Blender installation

Blender 5.2.2 LTS is installed from the official portable ZIP at D:\Blender\5.2.2\blender-5.2.2-windows-x64\blender.exe. The Blender Lab MCP add-on requires Blender 5.1 or newer.

## Start Blender MCP

The official Blender Lab MCP extension 1.0.0 is installed and enabled in the Blender 5.2 user profile, with Auto Start on. Blender's saved Allow Online Access preference remains off. The launcher D:\Blender\Start Blender MCP.cmd starts Blender with the documented --online-mode override for that process.

1. Start D:\Blender\Start Blender MCP.cmd.
2. Check that the extension reports the local server at 127.0.0.1:9876.
3. Restart Codex to load the registered mu_art_pipeline and mu_blender servers.

## Python environment and MCP configuration

The project environment is at repository root .venv. Use .agents/skills/mu-art-pipeline/scripts/sync.ps1 to install dependencies. Both MCP entries in the user-level Codex config.toml must set UV_PROJECT_ENVIRONMENT to E:/Projects/MuMain/.venv; see pipeline.md for the TOML block.

The Blender tools expose scene inspection, mesh creation, materials and transforms, workspace texture loading, interchange import/export, BMD import/export, and saving editable .blend projects. Imported BMDs get a weighted armature and one Action per source action. Exporting an imported model retains its skeleton and original BMD action data while writing edited geometry; Blender Action edits are not encoded into the BMD. New models export as static geometry. File operations are restricted to the pipeline workspace, not src/bin/Data.

The experimental Blender integration can execute LLM-generated Python in Blender. Keep original game assets outside its write workflow and use a separate working copy of .blend projects.
