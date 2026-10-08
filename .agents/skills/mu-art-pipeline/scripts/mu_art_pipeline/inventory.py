"""Read-only inventory helpers for the game's on-disk assets."""

from __future__ import annotations

import hashlib
import os
from collections import Counter
from pathlib import Path
from typing import Any


MODEL_EXTENSIONS = {".bmd"}
MODEL_SOURCE_EXTENSIONS = {".blend", ".dae", ".fbx", ".glb", ".gltf", ".obj", ".smd"}
TEXTURE_EXTENSIONS = {".bmp", ".dds", ".jpeg", ".jpg", ".ozj", ".ozt", ".png", ".tga"}
MAP_EXTENSIONS = {".att", ".att1", ".map"}
SKIP_DIRECTORY_NAMES = {".git", ".venv", "__pycache__", "node_modules"}


def find_repository_root(start: Path | None = None) -> Path:
    """Find the checkout containing the client's Data directory."""
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "src" / "bin" / "Data").is_dir():
            return candidate
    raise FileNotFoundError("Could not find a repository containing src/bin/Data.")


def classify_asset(path: Path) -> str:
    extension = path.suffix.lower()
    if extension in MODEL_EXTENSIONS:
        return "model"
    if extension in MODEL_SOURCE_EXTENSIONS:
        return "model_source"
    if extension in TEXTURE_EXTENSIONS:
        return "texture"
    if extension in MAP_EXTENSIONS:
        return "map"
    return "other"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as asset_file:
        for chunk in iter(lambda: asset_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_inventory(
    data_root: Path,
    include_files: bool = False,
    hash_files: bool = False,
    file_limit: int | None = None,
) -> dict[str, Any]:
    """Summarize assets and optionally include a file-level manifest."""
    root = data_root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Asset directory does not exist: {root}")

    extension_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    file_records: list[dict[str, Any]] = []
    total_bytes = 0

    for directory, subdirectories, filenames in os.walk(root, followlinks=False):
        directory_path = Path(directory)
        subdirectories[:] = sorted(
            name
            for name in subdirectories
            if name not in SKIP_DIRECTORY_NAMES
            and not (directory_path / name).is_symlink()
        )

        for filename in sorted(filenames):
            asset_path = directory_path / filename
            if asset_path.is_symlink():
                continue
            try:
                size_bytes = asset_path.stat(follow_symlinks=False).st_size
            except OSError as error:
                raise OSError(f"Could not read asset metadata for {asset_path}: {error}") from error

            extension = asset_path.suffix.lower() or "[no extension]"
            category = classify_asset(asset_path)
            total_bytes += size_bytes
            extension_counts[extension] += 1
            category_counts[category] += 1

            if include_files and (file_limit is None or len(file_records) < file_limit):
                record: dict[str, Any] = {
                    "path": asset_path.relative_to(root).as_posix(),
                    "extension": extension,
                    "category": category,
                    "size_bytes": size_bytes,
                }
                if hash_files:
                    record["sha256"] = _sha256(asset_path)
                file_records.append(record)

    result: dict[str, Any] = {
        "schema_version": 1,
        "data_root": str(root),
        "asset_count": sum(category_counts.values()),
        "total_bytes": total_bytes,
        "count_by_category": dict(sorted(category_counts.items())),
        "count_by_extension": dict(sorted(extension_counts.items())),
    }
    if include_files:
        result["assets"] = file_records
    return result
