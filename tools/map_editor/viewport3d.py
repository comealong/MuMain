"""Perspective software viewport for native MuMain terrain and BMD meshes."""
from __future__ import annotations

import math
from typing import Any

from PIL import Image, ImageDraw

TILE_WORLD_SIZE = 100.0
HEIGHT_WORLD_FACTOR = 1.5
HEIGHT_EXAGGERATION = 3.0


class Viewport3D:
    def __init__(self) -> None:
        self.yaw = -0.75
        self.pitch = 0.58
        self.distance = 42000.0
        self.target_x = 12800.0
        self.target_y = 12800.0
        self.target_z = 0.0
        self._last_size = (800, 600)
        self._object_points: list[tuple[float, float, int]] = []

    def orbit(self, dx: float, dy: float) -> None:
        self.yaw += dx * 0.008
        self.pitch = max(0.12, min(1.25, self.pitch + dy * 0.006))

    def zoom(self, wheel_delta: float) -> None:
        factor = 0.86 if wheel_delta > 0 else 1.16
        self.distance = max(5000.0, min(100000.0, self.distance * factor))

    def _camera_point(self, x: float, y: float, height: float) -> tuple[float, float, float]:
        dx = x * TILE_WORLD_SIZE - self.target_x
        dy = y * TILE_WORLD_SIZE - self.target_y
        dz = height * HEIGHT_WORLD_FACTOR * HEIGHT_EXAGGERATION - self.target_z
        c, s = math.cos(self.yaw), math.sin(self.yaw)
        horizontal = c * dx - s * dy
        depth_axis = s * dx + c * dy
        depth = self.distance + depth_axis * math.cos(self.pitch) - dz * math.sin(self.pitch)
        vertical = depth_axis * math.sin(self.pitch) + dz * math.cos(self.pitch)
        return horizontal, vertical, depth

    def _project(self, point: tuple[float, float, float], width: int, height: int) -> tuple[float, float, float]:
        x, up, depth = point
        focal = min(width, height) * 1.25
        if depth <= 1.0:
            return -10000.0, -10000.0, depth
        return width * 0.5 + focal * x / depth, height * 0.53 - focal * up / depth, depth

    @staticmethod
    def _blend_color(mapping, index: int, tile_colors: list[tuple[int, int, int]]) -> tuple[int, int, int]:
        slot1 = mapping.layer1[index] % len(tile_colors)
        base = tile_colors[slot1]
        alpha = mapping.alpha[index] / 255.0
        if alpha == 0.0:
            return base
        slot2 = mapping.layer2[index] % len(tile_colors)
        overlay = tile_colors[slot2]
        return tuple(round(base[c] * (1.0-alpha) + overlay[c] * alpha) for c in range(3))

    @staticmethod
    def _shade(color: tuple[int, int, int], a, b, c) -> tuple[int, int, int]:
        ux, uy, uz = b[0]-a[0], b[1]-a[1], b[2]-a[2]
        vx, vy, vz = c[0]-a[0], c[1]-a[1], c[2]-a[2]
        nx, ny, nz = uy*vz-uz*vy, uz*vx-ux*vz, ux*vy-uy*vx
        length = math.sqrt(nx*nx+ny*ny+nz*nz) or 1.0
        light = max(0.35, min(1.18, 0.62 + (0.4*nz - 0.2*nx - 0.15*ny) / length))
        return tuple(max(0, min(255, int(channel*light))) for channel in color)

    def render(self, width: int, height: int, mapping, heights: bytearray,
               tile_colors: list[tuple[int, int, int]], objects: list[Any],
               models: dict[int, dict[str, Any]], mode: str = "Texture",
               attributes: bytearray | None = None) -> Image.Image:
        width, height = max(320, width), max(240, height)
        self._last_size = width, height
        image = Image.new("RGB", (width, height), (31, 37, 47))
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, height*0.45, width, height), fill=(42, 45, 51))
        step = 4 if self.distance > 26000 else 2 if self.distance > 14000 else 1
        primitives = []

        def terrain_vertex(x: int, y: int):
            index = min(255, y) * 256 + min(255, x)
            h = heights[index] if heights is not None else 0
            raw = self._camera_point(x, y, h)
            screen = self._project(raw, width, height)
            return raw, screen

        rows = list(range(0, 256, step))
        cols = list(range(0, 256, step))
        if rows[-1] != 255: rows.append(255)
        if cols[-1] != 255: cols.append(255)
        row_vertices = [[terrain_vertex(x, y) for x in cols] for y in rows]
        for yi in range(len(rows)-1):
            y0, y1 = rows[yi], rows[yi+1]
            for xi in range(len(cols)-1):
                x0, x1 = cols[xi], cols[xi+1]
                quad = [row_vertices[yi][xi], row_vertices[yi][xi+1],
                        row_vertices[yi+1][xi+1], row_vertices[yi+1][xi]]
                screen = [point[1] for point in quad]
                if max(p[0] for p in screen) < 0 or min(p[0] for p in screen) > width or max(p[1] for p in screen) < 0 or min(p[1] for p in screen) > height:
                    continue
                depth = sum(point[2] for point in screen) / 4.0
                map_index = y0 * 256 + x0
                if mode == "Attribute" and attributes is not None:
                    value = attributes[map_index] & ~0x02
                    color = ((18, 20, 24) if value & 8 else (220, 56, 64) if value & 4
                             else (50, 126, 222) if value & 16 else (44, 190, 96) if value & 1
                             else (68, 130, 77))
                elif mode == "Height":
                    level = heights[map_index]
                    color = (level, level, level)
                else:
                    color = self._blend_color(mapping, map_index, tile_colors)
                world = [point[0] for point in quad]
                shaded = self._shade(color, world[0], world[1], world[3])
                primitives.append((depth, screen, shaded, "terrain"))

        self._object_points.clear()
        for object_index, obj in enumerate(objects):
            origin = self._camera_point(obj.x / TILE_WORLD_SIZE, obj.y / TILE_WORLD_SIZE,
                                       obj.z / (HEIGHT_WORLD_FACTOR * HEIGHT_EXAGGERATION))
            sx, sy, _ = self._project(origin, width, height)
            self._object_points.append((sx, sy, object_index))
            model = models.get(obj.type_id)
            if model is None:
                continue
            angle = math.radians(obj.angle_z)
            ca, sa = math.cos(angle), math.sin(angle)
            scale = max(0.01, obj.scale)
            for mesh in model.get("meshes", []):
                vertices = mesh.get("vertices", [])
                transformed = []
                for vertex in vertices:
                    vx, vy, vz = vertex["position"]
                    wx = obj.x + scale * (vx*ca - vy*sa)
                    wy = obj.y + scale * (vx*sa + vy*ca)
                    wz = obj.z + scale * vz
                    raw = self._camera_point(wx / TILE_WORLD_SIZE, wy / TILE_WORLD_SIZE,
                                             wz / (HEIGHT_WORLD_FACTOR * HEIGHT_EXAGGERATION))
                    transformed.append((raw, self._project(raw, width, height)))
                material = mesh.get("preview_color", (158, 143, 105))
                for triangle in mesh.get("triangles", []):
                    face = [transformed[index] for index in triangle.get("vertices", [])]
                    if len(face) < 3 or any(item[1][2] <= 1.0 for item in face): continue
                    screen = [item[1] for item in face]
                    if max(p[0] for p in screen) < 0 or min(p[0] for p in screen) > width or max(p[1] for p in screen) < 0 or min(p[1] for p in screen) > height:
                        continue
                    depth = sum(point[2] for point in screen) / len(screen)
                    world = [point[0] for point in face]
                    primitives.append((depth, screen, self._shade(material, world[0], world[1], world[2]), "object"))

        primitives.sort(key=lambda item: item[0], reverse=True)
        for _depth, points, color, _kind in primitives:
            draw.polygon([(p[0], p[1]) for p in points], fill=color)
            draw.line([(p[0], p[1]) for p in points] + [(points[0][0], points[0][1])], fill=tuple(max(0, c-12) for c in color), width=1)
        for sx, sy, object_index in self._object_points:
            if 0 <= sx < width and 0 <= sy < height:
                draw.ellipse((sx-4, sy-4, sx+4, sy+4), fill=(250, 227, 113), outline=(30, 30, 30))
        draw.text((12, 10), f"3D terrain  ·  LOD {step}  ·  drag middle mouse to orbit  ·  wheel to zoom", fill=(235, 239, 245))
        return image

    def pick_cell(self, screen_x: float, screen_y: float) -> tuple[int, int] | None:
        width, height = self._last_size
        focal = min(width, height) * 1.25
        vertical_projection = (height * 0.53 - screen_y) / focal
        denominator = math.sin(self.pitch) - vertical_projection * math.cos(self.pitch)
        if abs(denominator) < 1e-5:
            return None
        depth_axis = vertical_projection * self.distance / denominator
        depth = self.distance + depth_axis * math.cos(self.pitch)
        horizontal = (screen_x - width*0.5) * depth / focal
        c, s = math.cos(self.yaw), math.sin(self.yaw)
        dx = c * horizontal + s * depth_axis
        dy = -s * horizontal + c * depth_axis
        x = round((self.target_x + dx) / TILE_WORLD_SIZE)
        y = round((self.target_y + dy) / TILE_WORLD_SIZE)
        if 0 <= x < 256 and 0 <= y < 256:
            return x, y
        return None

    def pick_object(self, x: float, y: float, radius: float = 16.0) -> int | None:
        nearest = min(self._object_points, key=lambda p: (p[0]-x)**2 + (p[1]-y)**2, default=None)
        if nearest is None or (nearest[0]-x)**2 + (nearest[1]-y)**2 > radius*radius:
            return None
        return nearest[2]
