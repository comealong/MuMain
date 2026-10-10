# MuMain Art Pipeline

Python CLI and MCP tools for repeatable inspection and conversion of MuMain client art assets. The implementation and workflow docs live in this Skill; the root pyproject.toml packages its scripts and the root .venv runs them. Generated work belongs in tools/art_pipeline/workspace.

## Environment

Install uv, then from the repository root run:

    ./.agents/skills/mu-art-pipeline/scripts/sync.ps1
    ./.agents/skills/mu-art-pipeline/scripts/run.ps1 mu-art doctor

The Python environment is the ignored repository-root .venv. The scripts set UV_PROJECT_ENVIRONMENT for every uv invocation, including MCP startup. Python 3.11 or newer is required.

## Commands

Inventory checked-in client data:

    ./.agents/skills/mu-art-pipeline/scripts/run.ps1 mu-art inventory

Write a file-level JSON manifest, optionally including SHA-256 hashes:

    ./.agents/skills/mu-art-pipeline/scripts/run.ps1 mu-art inventory --manifest .cache/art-assets.json --hash

Decode or encode OZJ/OZT textures in the workspace:

    ./.agents/skills/mu-art-pipeline/scripts/run.ps1 mu-art texture decode src/bin/Data/Effect/Fire01.OZJ --output tools/art_pipeline/workspace/Fire01.jpg
    ./.agents/skills/mu-art-pipeline/scripts/run.ps1 mu-art texture encode tools/art_pipeline/workspace/Fire01.jpg --output tools/art_pipeline/workspace/Fire01.OZJ

OZJ has a 24-byte wrapper before JPEG; OZT has a 4-byte wrapper before 32-bit uncompressed TGA. The client supports textures up to 1024x1024. Encoding refuses to overwrite an existing output unless --force is passed. JPEG has no alpha; use OZT/TGA when transparency must be kept.

Inspect a generated BMD:

    ./.agents/skills/mu-art-pipeline/scripts/run.ps1 mu-art model inspect tools/art_pipeline/workspace/exports/stone_gate.bmd

The report separates polygon faces, triangulated triangle count, and quads so a flat or low-poly mesh is easier to identify. This checks file structure; inspect appearance in Blender and validate placement in the target client before shipping.

Install a reviewed model and any textures exported beside it into the repository client Data directory. Preview destinations and unresolved texture references first:

    ./.agents/skills/mu-art-pipeline/scripts/run.ps1 mu-art install exports/stone_gate.bmd --target Object/stone_gate.bmd --dry-run

After reviewing the plan, omit --dry-run to install. Existing files are never replaced unless --overwrite is supplied; replacements are backed up under tools/art_pipeline/workspace/backups. Use the correct Data-relative target directory for the resource type. By default this copies into the repository data tree. To target a separate running client, pass its Data folder with --data-root, for example --data-root D:/Games/MuMain/Data. Backups remain in the repository workspace.

## MCP servers

Both user-level Codex MCP server entries must set UV_PROJECT_ENVIRONMENT to E:/Projects/MuMain/.venv. Keep the current uv run commands and add the environment mapping:

    [mcp_servers.mu_art_pipeline]
    command = "uv"
    args = ["run", "--project", "E:/Projects/MuMain", "mu-art-mcp"]
    env = { UV_PROJECT_ENVIRONMENT = "E:/Projects/MuMain/.venv" }

    [mcp_servers.mu_blender]
    command = "uv"
    args = ["run", "--project", "E:/Projects/MuMain", "mu-blender-mcp"]
    env = { UV_PROJECT_ENVIRONMENT = "E:/Projects/MuMain/.venv" }

Restart Codex after changing MCP configuration. The asset server reads below src/bin/Data and stages requested originals into the ignored workspace; it does not overwrite game assets.

## BMD models

The project reads unencrypted v10 and encrypted v12 client BMD models. import_bmd creates mesh objects, a weighted Blender armature, and one Action per source action, retaining UVs and custom normals.

For an imported animated model, export the edited mesh with its source rig still present. The exporter writes the selected/evaluated geometry and preserves the source skeleton and original action records. Changes to Blender animation Actions are not encoded into those BMD action records. For a new model, the exporter writes a static one-frame model with a root bone. Connected material images become OZT files in a sibling texture folder. Verify outputs in Blender and the target client before installation.

See blender-mcp-setup.md for the Blender integration and connection details.

## Character recovery and texture alignment

Preserve separate body meshes on one shared source armature with source actions, UVs, textures, and node assignments. Determine the actual client body-slot and resource mapping before assembling a character; convenience scripts may contain preset asset selections.

Read [Reference spaces, assembly, and textures](character-model-assembly-and-textures.md) for coordinate conversion, source metadata, UV handling, and reusable pose/rig/mesh modules. Recovery starts from original resources; an authorized local remodel can continue from its saved baseline. Explicit topology changes follow [restyling and deformation repair](character-restyling.md).

## Proportions, attachments, and actions

- [Proportion and animation reuse](character-proportions-and-animation-reuse.md): adapt the skeleton and reference mesh, then inspect movement and contacts.
- [Rigid attachment composition](weapon-attachment.md): trace the actual client branch and combine socket, item pose, and instance transforms.
- [Action lookup and time conventions](player-action-index.md): derive IDs and names from current source/asset data rather than a historical table.

Generate resource-specific action catalogs with .venv/Scripts/python.exe .agents/skills/mu-art-pipeline/scripts/extract_player_actions.py. Catalogs and experiment records remain in the workspace; the skill keeps reusable methods.
