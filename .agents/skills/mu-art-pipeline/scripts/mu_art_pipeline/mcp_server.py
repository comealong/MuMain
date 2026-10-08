"""Read-only MCP tools for inspecting MuMain assets."""

from __future__ import annotations

import shutil
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from PIL import Image, UnidentifiedImageError

from .inventory import build_inventory, find_repository_root
from .textures import convert_texture


server = FastMCP("MuMain Art Pipeline")


def _data_root() -> Path:
    return (find_repository_root() / "src" / "bin" / "Data").resolve()


def _workspace() -> Path:
    workspace = find_repository_root() / "tools" / "art_pipeline" / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace.resolve()


def _inside(path: Path, root: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"{label} must stay inside {root}.")
    return resolved


@server.tool()
def list_game_assets(subdirectory: str = "", limit: int = 100) -> dict[str, object]:
    """Summarize client assets; optionally return matching files under a Data subdirectory."""
    data_root = _data_root()
    requested_root = _inside(data_root / subdirectory, data_root, "The requested directory")
    if limit < 1 or limit > 1000:
        raise ValueError("limit must be between 1 and 1000.")

    inventory = build_inventory(requested_root, include_files=True, file_limit=limit)
    assets = inventory["assets"]
    inventory["returned_count"] = len(assets)
    inventory["truncated"] = inventory["asset_count"] > len(assets)
    return inventory


@server.tool()
def inspect_texture(relative_path: str) -> dict[str, object]:
    """Read image dimensions and color mode for a common editable texture under Data."""
    data_root = _data_root()
    texture_path = _inside(data_root / relative_path, data_root, "The texture path")
    if texture_path.suffix.lower() not in {".bmp", ".jpeg", ".jpg", ".png", ".tga"}:
        raise ValueError("This inspector supports BMP, JPEG, PNG, and TGA files.")
    if not texture_path.is_file():
        raise FileNotFoundError(f"Texture not found: {relative_path}")

    try:
        with Image.open(texture_path) as image:
            return {
                "path": texture_path.relative_to(data_root).as_posix(),
                "width": image.width,
                "height": image.height,
                "mode": image.mode,
                "format": image.format,
            }
    except UnidentifiedImageError as error:
        raise ValueError(f"Pillow could not identify {relative_path}.") from error


@server.tool()
def stage_asset(relative_path: str) -> dict[str, object]:
    """Copy one game asset to the isolated art-pipeline workspace without replacing files."""
    data_root = _data_root()
    workspace = _workspace()
    source = _inside(data_root / relative_path, data_root, "The source path")
    if not source.is_file():
        raise FileNotFoundError(f"Game asset not found: {relative_path}")
    destination = _inside(workspace / relative_path, workspace, "The staged path")
    if destination.exists():
        raise FileExistsError(f"Workspace file already exists: {destination.relative_to(workspace).as_posix()}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return {"source": source.relative_to(data_root).as_posix(), "staged": destination.relative_to(workspace).as_posix()}


@server.tool()
def convert_workspace_texture(relative_path: str, overwrite: bool = False) -> dict[str, object]:
    """Convert OZJ to JPEG or OZT to TGA (and back) inside the isolated workspace."""
    workspace = _workspace()
    source = _inside(workspace / relative_path, workspace, "The texture path")
    return convert_texture(source, overwrite=overwrite)


def main() -> None:
    server.run(transport="stdio")
