"""Encode and decode the client's OZJ and OZT texture wrappers."""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, UnidentifiedImageError


MAX_TEXTURE_WIDTH = 1024
MAX_TEXTURE_HEIGHT = 1024
WRAPPER_HEADER_BYTES = {".ozj": 24, ".ozt": 4}


def _validate_image_payload(payload: bytes, extension: str) -> tuple[int, int]:
    try:
        with Image.open(io.BytesIO(payload)) as image:
            width, height = image.size
            if width <= 0 or height <= 0:
                raise ValueError("Texture dimensions must be positive.")
            if width > MAX_TEXTURE_WIDTH or height > MAX_TEXTURE_HEIGHT:
                raise ValueError(
                    f"Texture is {width}x{height}; the client limit is "
                    f"{MAX_TEXTURE_WIDTH}x{MAX_TEXTURE_HEIGHT}."
                )
            image.verify()
    except UnidentifiedImageError as error:
        raise ValueError(f"Could not identify {extension} texture data.") from error

    if extension == ".tga":
        if len(payload) < 18:
            raise ValueError("TGA file is shorter than its 18-byte header.")
        color_map_type = payload[1]
        image_type = payload[2]
        bits_per_pixel = payload[16]
        if color_map_type != 0 or image_type != 2 or bits_per_pixel != 32:
            raise ValueError("OZT requires an uncompressed 32-bit true-color TGA without a color map.")
    return width, height


def convert_texture(source: Path, destination: Path | None = None, overwrite: bool = False) -> dict[str, object]:
    """Convert OZJ to JPEG or OZT to TGA, and encode them in the opposite direction."""
    source_path = source.resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"Texture source does not exist: {source_path}")

    extension = source_path.suffix.lower()
    if extension in WRAPPER_HEADER_BYTES:
        header_bytes = WRAPPER_HEADER_BYTES[extension]
        wrapped_bytes = source_path.read_bytes()
        if len(wrapped_bytes) <= header_bytes:
            raise ValueError(f"{source_path.name} is shorter than its {header_bytes}-byte wrapper header.")
        image_extension = ".jpg" if extension == ".ozj" else ".tga"
        image_bytes = wrapped_bytes[header_bytes:]
        width, height = _validate_image_payload(image_bytes, image_extension)
        output_extension = image_extension
        output_bytes = image_bytes
    elif extension in {".jpg", ".jpeg", ".tga"}:
        image_bytes = source_path.read_bytes()
        width, height = _validate_image_payload(image_bytes, extension)
        output_extension = ".ozj" if extension in {".jpg", ".jpeg"} else ".ozt"
        prefix_size = WRAPPER_HEADER_BYTES[output_extension]
        if len(image_bytes) <= prefix_size:
            raise ValueError(f"{source_path.name} is too short to wrap.")
        output_bytes = image_bytes[:prefix_size] + image_bytes
    else:
        raise ValueError("Supported conversions: OZJ/JPEG and OZT/TGA.")

    output_path = destination.resolve() if destination is not None else source_path.with_suffix(output_extension)
    if output_path == source_path:
        raise ValueError("Input and output paths must be different.")
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"Output already exists; pass --force to replace it: {output_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(output_bytes)
    return {
        "source": str(source_path),
        "output": str(output_path),
        "width": width,
        "height": height,
        "bytes_written": len(output_bytes),
    }
