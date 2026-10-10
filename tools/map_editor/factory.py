"""Create blank, game-readable map folders from an existing world's assets."""
from __future__ import annotations

from pathlib import Path
import shutil
import tempfile

import formats

RESOURCE_PREFIXES = ("tile", "exttile", "alphatile", "terrainlight", "terraingrass")


def _world_number(folder: Path) -> int:
    suffix = folder.name.lower().removeprefix("world")
    if not suffix.isdigit():
        raise ValueError("The source folder must be named WorldN.")
    return int(suffix)


def _copy_map_resources(source: Path, target: Path) -> None:
    for item in source.iterdir():
        if item.is_file() and item.name.lower().startswith(RESOURCE_PREFIXES):
            shutil.copy2(item, target / item.name)


def create_blank_map(data_folder: Path, source_world: Path, world_number: int) -> dict[str, object]:
    """Create WorldN native files and copy its terrain textures from a source world."""
    if not 1 <= world_number <= 255:
        raise ValueError("World folder number must be between 1 and 255.")
    if not source_world.is_dir():
        raise FileNotFoundError(f"Source world folder not found: {source_world}")
    source_number = _world_number(source_world)
    source_map = source_world / f"EncTerrain{source_number}.map"
    source_height = source_world / "TerrainHeight.OZB"
    if not source_map.is_file() or not source_height.is_file():
        raise ValueError("The source world must contain EncTerrainN.map and TerrainHeight.OZB.")

    destination = data_folder / f"World{world_number}"
    if destination.exists():
        raise FileExistsError(f"Destination already exists: {destination}")
    data_folder.mkdir(parents=True, exist_ok=True)

    stage_root = Path(tempfile.mkdtemp(prefix=f".World{world_number}.", dir=data_folder))
    stage_world = stage_root / destination.name
    stage_world.mkdir()
    try:
        _copy_map_resources(source_world, stage_world)
        _, height_prefix, height_header = formats.read_height(source_height)
        terrain = formats.TerrainMap(0, world_number, bytearray(formats.CELLS),
                                     bytearray([255]) * formats.CELLS, bytearray(formats.CELLS))
        formats.write_mapping(stage_world / f"EncTerrain{world_number}.map", terrain)
        attributes = formats.TerrainAttributes(0, world_number, 255, 255,
                                                bytearray(formats.CELLS), 1)
        formats.write_attributes(stage_world / f"EncTerrain{world_number}.att", attributes)
        formats.write_objects(stage_world / f"EncTerrain{world_number}.obj", 0, world_number, [])
        formats.write_height(stage_world / "TerrainHeight.OZB", bytearray(formats.CELLS),
                             height_prefix, height_header)

        source_objects = data_folder / f"Object{source_number}"
        destination_objects = data_folder / f"Object{world_number}"
        objects_copied = False
        if source_objects.is_dir() and not destination_objects.exists() and source_number != world_number:
            shutil.copytree(source_objects, stage_root / destination_objects.name)
            objects_copied = True

        destination.parent.mkdir(parents=True, exist_ok=True)
        stage_world.replace(destination)
        if objects_copied:
            (stage_root / destination_objects.name).replace(destination_objects)
        return {"world_folder": destination, "objects_copied": objects_copied,
                "source_world": source_world, "world_number": world_number}
    except Exception:
        shutil.rmtree(stage_root, ignore_errors=True)
        raise
    finally:
        if stage_root.exists():
            shutil.rmtree(stage_root, ignore_errors=True)
