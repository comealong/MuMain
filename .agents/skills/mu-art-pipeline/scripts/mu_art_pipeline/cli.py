"""Command line interface for the MuMain asset pipeline."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

from . import __version__
from .bmd import parse_bmd
from .deployment import install_workspace_asset, plan_workspace_install
from .inventory import build_inventory, find_repository_root
from .textures import convert_texture


def _configure_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(errors="backslashreplace")


def _default_data_root() -> Path:
    return find_repository_root() / "src" / "bin" / "Data"


def _run_version(executable: str | None, arguments: list[str]) -> str | None:
    if executable is None:
        return None
    try:
        result = subprocess.run(
            [executable, *arguments],
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return (result.stdout or result.stderr).splitlines()[0].strip()


def _find_blender() -> str | None:
    configured_path = os.environ.get("BLENDER_EXECUTABLE")
    if configured_path and Path(configured_path).is_file():
        return configured_path
    executable = shutil.which("blender")
    if executable:
        return executable
    local_app_data = os.environ.get("LOCALAPPDATA")
    candidates = [
        Path("D:/Blender/5.2.2/blender-5.2.2-windows-x64/blender.exe"),
        Path("D:/Blender/5.2.2/blender.exe"),
        Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Blender Foundation" / "Blender 5.2" / "blender.exe",
        Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Blender Foundation" / "Blender 5.1" / "blender.exe",
    ]
    if local_app_data:
        candidates.extend([
            Path(local_app_data) / "Programs" / "Blender Foundation" / "Blender 5.2" / "blender.exe",
            Path(local_app_data) / "Programs" / "Blender Foundation" / "Blender 5.1" / "blender.exe",
        ])
    return next((str(candidate) for candidate in candidates if candidate.is_file()), None)


def _doctor() -> dict[str, object]:
    return {
        "art_pipeline": __version__,
        "python": sys.version.split()[0],
        "uv": _run_version(shutil.which("uv"), ["--version"]),
        "blender": _run_version(_find_blender(), ["--version"]),
        "repository_root": str(find_repository_root()),
        "data_directory": str(_default_data_root()),
    }


def _mesh_topology(mesh: dict[str, Any]) -> dict[str, int]:
    polygons = mesh["triangles"]
    polygon_sizes = [polygon["size"] for polygon in polygons]
    return {
        "vertices": len(mesh["vertices"]),
        "polygons": len(polygon_sizes),
        "triangles": sum(size - 2 for size in polygon_sizes),
        "quads": sum(size == 4 for size in polygon_sizes),
    }


def _write_json(value: object, output_path: Path | None) -> None:
    rendered = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if output_path is None:
        sys.stdout.write(rendered)
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    print(f"Wrote {output_path}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mu-art",
        description="Inspect and prepare MuMain client art assets.",
    )
    parser.add_argument("--version", action="version", version=f"mu-art {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("doctor", help="Report Python, uv, Blender, and asset paths.")

    inventory = commands.add_parser("inventory", help="Count assets under the client Data directory.")
    inventory.add_argument("--data-root", type=Path, default=None, help="Override the Data directory.")
    inventory.add_argument("--manifest", type=Path, help="Write a JSON file-level manifest.")
    inventory.add_argument("--hash", action="store_true", help="Add SHA-256 for each manifest entry.")

    texture = commands.add_parser("texture", help="Decode or encode OZJ/JPEG and OZT/TGA textures.")
    texture_commands = texture.add_subparsers(dest="texture_action", required=True)
    for action in ("decode", "encode"):
        texture_command = texture_commands.add_parser(action)
        texture_command.add_argument("source", type=Path)
        texture_command.add_argument("--output", type=Path, default=None)
        texture_command.add_argument("--force", action="store_true", help="Replace an existing output file.")
    install = commands.add_parser("install", help="Install a validated workspace asset into client Data.")
    install.add_argument("source", help="Workspace-relative BMD, OZJ, or OZT path.")
    install.add_argument("--target", required=True, help="Destination relative to the selected Data directory.")
    install.add_argument("--data-root", type=Path, default=None, help="Override the client Data directory.")
    install.add_argument("--overwrite", action="store_true", help="Back up and replace existing destination files.")
    install.add_argument("--dry-run", action="store_true", help="Show the files and texture dependencies without installing.")

    model = commands.add_parser("model", help="Inspect MU Online BMD models.")
    model_commands = model.add_subparsers(dest="model_action", required=True)
    inspect_model = model_commands.add_parser("inspect", help="Validate a BMD and summarize its contents.")
    inspect_model.add_argument("source", type=Path)
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    _configure_console()
    parser = _build_parser()
    options = parser.parse_args(arguments)
    try:
        if options.command == "doctor":
            _write_json(_doctor(), None)
            return 0

        if options.command == "install":
            if options.dry_run:
                result = plan_workspace_install(options.source, options.target, options.data_root)
                result["dry_run"] = True
            else:
                result = install_workspace_asset(
                    options.source, options.target, options.overwrite, options.data_root
                )
            _write_json(result, None)
            return 0

        if options.command == "texture":
            source_extension = options.source.suffix.lower()
            if options.texture_action == "decode" and source_extension not in {".ozj", ".ozt"}:
                raise ValueError("decode expects a .ozj or .ozt source.")
            if options.texture_action == "encode" and source_extension not in {".jpg", ".jpeg", ".tga"}:
                raise ValueError("encode expects a .jpg, .jpeg, or .tga source.")
            result = convert_texture(options.source, options.output, overwrite=options.force)
            _write_json(result, None)
            return 0

        if options.command == "model":
            model = parse_bmd(options.source)
            _write_json({
                "file": str(options.source.resolve()),
                "name": model["name"],
                "version": model["version"],
                "meshes": [
                    {
                        **_mesh_topology(mesh),
                        "texture": mesh["texture"],
                    }
                    for mesh in model["meshes"]
                ],
                "bones": len(model["bones"]),
                "actions": [action["keys"] for action in model["actions"]],
            }, None)
            return 0

        data_root = options.data_root or _default_data_root()
        include_files = options.manifest is not None
        inventory = build_inventory(data_root, include_files=include_files, hash_files=options.hash)
        _write_json(inventory, options.manifest)
        return 0
    except (FileNotFoundError, OSError, ValueError) as error:
        print(f"mu-art: {error}", file=sys.stderr)
        return 2
