"""Plan and safely install prepared art assets into the client Data directory."""

from __future__ import annotations

import os
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath

from .bmd import parse_bmd
from .inventory import find_repository_root
from .textures import convert_texture


INSTALLABLE_EXTENSIONS = {".bmd", ".ozj", ".ozt"}
TEXTURE_EXTENSIONS = {".ozj", ".ozt"}


def _workspace_root() -> Path:
    return (find_repository_root() / "tools" / "art_pipeline" / "workspace").resolve()


def _inside_root(root: Path, relative_path: str, label: str) -> Path:
    if Path(relative_path).is_absolute() or PureWindowsPath(relative_path).is_absolute():
        raise ValueError(f"{label} must be a relative path.")
    candidate = (root / relative_path).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError(f"{label} must stay inside {root}.")
    return candidate


def _validate_texture(source: Path, workspace: Path) -> None:
    extension = source.suffix.lower()
    if extension not in TEXTURE_EXTENSIONS:
        raise ValueError(f"Game texture must use .ozj or .ozt: {source.name}")
    with tempfile.TemporaryDirectory(prefix=".mu-art-validate-", dir=workspace) as temporary:
        decoded_extension = ".jpg" if extension == ".ozj" else ".tga"
        convert_texture(source, Path(temporary) / f"validated{decoded_extension}")


def _install_files(
    source: Path,
    target: Path,
    workspace: Path,
) -> tuple[list[tuple[Path, Path]], list[str]]:
    files = [(source, target)]
    external_textures: list[str] = []
    if source.suffix.lower() != ".bmd":
        _validate_texture(source, workspace)
        return files, external_textures

    model = parse_bmd(source)
    texture_directory = (source.parent / f"{source.stem}_textures").resolve()
    if not texture_directory.is_relative_to(workspace):
        raise ValueError("The BMD texture directory escaped the workspace.")

    names = sorted({mesh["texture"] for mesh in model["meshes"] if mesh["texture"]})
    for name in names:
        if Path(name).name != name or PureWindowsPath(name).name != name:
            raise ValueError(f"BMD texture name must be a filename: {name}")
        texture = (texture_directory / name).resolve()
        if not texture.is_relative_to(texture_directory):
            raise ValueError(f"BMD texture escaped its export directory: {name}")
        if texture.is_file():
            _validate_texture(texture, workspace)
            files.append((texture, target.parent / name))
        elif not (target.parent / name).is_file():
            external_textures.append(name)
    return files, external_textures


def _resolve_roots(data_root: Path | None) -> tuple[Path, Path]:
    workspace = _workspace_root()
    root = data_root or (find_repository_root() / "src" / "bin" / "Data")
    root = root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Game Data directory does not exist: {root}")
    return workspace, root


def _plan_paths(
    source_relative_path: str,
    target_relative_path: str,
    data_root: Path | None,
) -> tuple[Path, Path, Path, list[tuple[Path, Path]], list[str]]:
    workspace, root = _resolve_roots(data_root)
    source = _inside_root(workspace, source_relative_path, "Source asset")
    if source.suffix.lower() not in INSTALLABLE_EXTENSIONS or not source.is_file():
        raise ValueError("Source must be a workspace BMD, OZJ, or OZT file.")
    target = _inside_root(root, target_relative_path, "Game target")
    if target.suffix.lower() != source.suffix.lower():
        raise ValueError("Source and target extensions must match.")
    files, external_textures = _install_files(source, target, workspace)
    destinations = [destination for _, destination in files]
    if len(set(destinations)) != len(destinations):
        raise ValueError("The installation bundle contains duplicate target filenames.")
    if any(source_path == destination for source_path, destination in files):
        raise ValueError("Workspace source and game destination must be different files.")
    if any(destination.exists() and not destination.is_file() for destination in destinations):
        raise ValueError("An installation target exists and is not a regular file.")
    return workspace, root, source, files, external_textures


def plan_workspace_install(
    source_relative_path: str,
    target_relative_path: str,
    data_root: Path | None = None,
) -> dict[str, object]:
    """Preview a workspace asset install without writing to game data."""
    workspace, root, source, files, external_textures = _plan_paths(
        source_relative_path, target_relative_path, data_root
    )
    return {
        "source": source.relative_to(workspace).as_posix(),
        "target_root": str(root),
        "files": [
            {
                "source": source_path.relative_to(workspace).as_posix(),
                "target": target_path.relative_to(root).as_posix(),
                "already_exists": target_path.exists(),
            }
            for source_path, target_path in files
        ],
        "external_textures": external_textures,
    }


def _backup_existing(
    files: list[tuple[Path, Path]],
    root: Path,
    workspace: Path,
) -> tuple[Path | None, dict[Path, Path]]:
    existing = [destination for _, destination in files if destination.exists()]
    if not existing:
        return None, {}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = (workspace / "backups" / f"{stamp}_{uuid.uuid4().hex[:8]}").resolve()
    if not backup_root.is_relative_to(workspace):
        raise ValueError("Backup directory escaped the workspace.")
    backups: dict[Path, Path] = {}
    for destination in existing:
        backup = backup_root / destination.relative_to(root)
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(destination, backup)
        backups[destination] = backup
    return backup_root, backups


def _copy_transaction(
    files: list[tuple[Path, Path]],
    root: Path,
    workspace: Path,
    overwrite: bool,
) -> tuple[Path | None, dict[Path, Path]]:
    conflicts = [destination for _, destination in files if destination.exists()]
    if conflicts and not overwrite:
        raise FileExistsError(f"Game target exists; rerun with overwrite enabled: {conflicts[0]}")

    temporary_files: dict[Path, Path] = {}
    committed: list[Path] = []
    backup_root: Path | None = None
    backups: dict[Path, Path] = {}
    try:
        for source, destination in files:
            destination.parent.mkdir(parents=True, exist_ok=True)
            handle, temporary_name = tempfile.mkstemp(
                prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
            )
            os.close(handle)
            temporary = Path(temporary_name)
            temporary_files[destination] = temporary
            shutil.copy2(source, temporary)

        backup_root, backups = _backup_existing(files, root, workspace)
        for _, destination in files:
            os.replace(temporary_files[destination], destination)
            committed.append(destination)
    except Exception:
        for destination in reversed(committed):
            backup = backups.get(destination)
            if backup is None:
                destination.unlink(missing_ok=True)
            else:
                shutil.copy2(backup, destination)
        raise
    finally:
        for temporary in temporary_files.values():
            temporary.unlink(missing_ok=True)
    return backup_root, backups


def install_workspace_asset(
    source_relative_path: str,
    target_relative_path: str,
    overwrite: bool = False,
    data_root: Path | None = None,
) -> dict[str, object]:
    """Install a validated BMD or OZJ/OZT bundle, backing up replaced files."""
    workspace, root, source, files, external_textures = _plan_paths(
        source_relative_path, target_relative_path, data_root
    )
    backup_root, backups = _copy_transaction(files, root, workspace, overwrite)
    return {
        "installed": [destination.relative_to(root).as_posix() for _, destination in files],
        "backups": [backup.relative_to(workspace).as_posix() for backup in backups.values()],
        "backup_directory": backup_root.relative_to(workspace).as_posix() if backup_root else None,
        "external_textures": external_textures,
    }
