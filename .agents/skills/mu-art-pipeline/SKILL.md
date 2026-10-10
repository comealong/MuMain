---
name: mu-art-pipeline
description: Use when inspecting, creating, importing, exporting, or editing 3D models and textures for the MuMain MU Online client, or when a natural-language request edits existing item or skill game data.
---

# MuMain game art workflow

Use the repository's Python and MCP tools for repeatable asset work. Stage originals and write generated art under tools/art_pipeline/workspace; keep src/bin/Data read-only during art preparation. Explicit item and skill data editing follows its separate contract below.

## Knowledge scope

Keep reusable methods, format conventions, tool contracts, and diagnostic criteria in this skill. Put model profiles, node/slot mappings for individual assets, action catalogs, fixed scene scripts, screenshots, numerical results, and experiment histories in the workspace. A successful case does not establish a universal proportion, pose, bone index, or acceptance threshold.

## Character recovery

Preserve independent body meshes on one shared source armature, including source actions, UVs, textures, and node assignments. Determine the target's actual client resource and slot mapping before assembling it. Start from original resources when recovering source geometry; use the appropriate saved experiment as the baseline for an authorized local revision.

Read [Character assembly, reference spaces, and textures](references/character-model-assembly-and-textures.md). Reuse the shared pose, rig, mesh, and staging modules; inspect any convenience entrypoint's preset resource selection before using it for a new target. Joining, welding, or remeshing changes geometry and belongs to an explicit remodeling task.

## Proportions and animation reuse

Read [Proportion changes and animation reuse](references/character-proportions-and-animation-reuse.md) when body components need different proportions while retaining source motion. Distinguish whole-object scaling, a final render transform, and a skeleton/mesh adaptation. Source animation translations, bind spaces, contacts, and root movement need separate treatment.

## Restyling and deformation repair

Read [Restyling, anatomy, seams, and skinning](references/character-restyling.md) for chibi conversion or shoulder, hand, knee, ankle, texture, and motion deformation problems. Build anatomical continuity before refining texture. A closed mesh and matching part seams do not prove adequate joint volume or smooth weights inside the surface.

Diagnose the reported pose with both clay and texture views. For spikes during motion, inspect adjacent weight gradients and posed edge stretch. Smooth weights on the shared outer surface while anchoring stable regions when appropriate; preserve rigid armor boundaries and hand contacts. Confirm the surrounding motion as well as the reported frame.

Reuse the generic anatomy, surface-weight solver, and Blender shared-binding modules listed in the restyling reference. Supply target-specific paths, regions, groups, coordinate frames, and tolerances from workspace configuration; the modules do not infer anatomy or save scenes.

## Attachments and action lookup

- Read [Rigid attachments and coordinate composition](references/weapon-attachment.md) for held or back-mounted items. Trace the actual client branch, preserve the item's own pose, and resolve sockets by source-node metadata. Attachment correctness and grip/contact correctness are separate checks.
- Read [Action lookup and frame conventions](references/player-action-index.md) to resolve source action IDs, enum aliases, conditional compilation, and frame/key mapping. Generate asset-specific action catalogs in the workspace; do not save those tables into skill guidance.

## Asset tools

- Discover and inspect assets with mu_art_pipeline, then stage source copies before conversion or editing. [Pipeline commands](references/pipeline.md) describe the CLI, packaging, environment, and installation workflow.
- Decode OZJ/OZT into editable JPEG/TGA and encode through the project texture tools. Preserve alpha and orientation; use the imagegen skill for requested raster generation or editing. A concept image is design guidance, not a UV atlas.
- Import BMD through mu_blender for source geometry, weighted armature, and source Actions. The imported-model exporter preserves original skeleton/action records; Blender Action edits are not automatically written into BMD animation data.
- For new or deliberately static geometry, export from a selected scene pose. For animated edits, first establish how the target format will represent the changed rig, channels, and bindings.
- Use interchange export for OBJ, FBX, glTF, or GLB, and save an editable Blend separately. Interchange files are not native client resources.

## Verify and hand off

Use checks that distinguish source-data fidelity, rest geometry, deformation, materials, attachments, and target-format compatibility. Inspect the saved output after reopening, including packed textures and requested comparisons. Record the actual inspected poses and limits in that experiment's report.

Generated BMD inspection proves structure; client appearance and runtime behavior require target-client verification. For an authorized installation, preview exact destinations with mu-art install --dry-run and retain replacement backups. Follow [pipeline commands](references/pipeline.md) for overwrite and target-directory options.

## Other workflows and setup

- [Natural-language item and skill editing](references/item-skill-editing.md): existing item definitions and skill records; preserve this workflow's independent authorization and scope.
- [Blender and MCP setup](references/blender-mcp-setup.md): local connection, environment, and workspace restrictions.
- [Asset formats and repository locations](../../../docs/art-assets.md).
