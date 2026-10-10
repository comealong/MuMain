"""Standalone 2D and 3D editor for MuMain map data."""
from __future__ import annotations

import struct
import io
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    from PIL import Image, ImageDraw, ImageTk
except ImportError as error:
    raise SystemExit("Map Editor requires Pillow. Install it with: python -m pip install Pillow") from error

import formats
import factory
from viewport3d import Viewport3D

SLOT_NAMES = [
    "TileGrass01", "TileGrass02", "TileGround01", "TileGround02", "TileGround03",
    "TileWater01", "TileWood01", "TileRock01", "TileRock02", "TileRock03",
    "TileRock04", "TileRock05", "TileRock06", "TileRock07",
] + [f"ExtTile{i:02d}" for i in range(1, 17)]
ATTRIBUTES = {"Walkable": 0, "Safezone": 1, "Blocked": 4, "No ground": 8, "Water": 16}
ATTR_COLORS = {0: (68, 130, 77), 1: (44, 190, 96), 4: (220, 56, 64), 8: (18, 20, 24), 16: (50, 126, 222)}
MODES = ("Texture", "Attribute", "Height", "Objects")
CELL_COUNT = formats.SIZE * formats.SIZE


def image_from_resource(path: Path) -> Image.Image | None:
    try:
        raw = path.read_bytes()
        suffix = path.suffix.lower()
        if suffix == ".ozj":
            raw = raw[24:]
        elif suffix == ".ozt":
            raw = raw[4:]
        return Image.open(io.BytesIO(raw)).convert("RGB")
    except (OSError, ValueError, IndexError):
        return None


class MapEditor(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("MuMain Map Editor")
        self.geometry("1280x850")
        self.minsize(960, 640)
        self.folder: Path | None = None
        self.mapping_path: Path | None = None
        self.attribute_path: Path | None = None
        self.object_path: Path | None = None
        self.height_path: Path | None = None
        self.mapping: formats.TerrainMap | None = None
        self.attributes: formats.TerrainAttributes | None = None
        self.height_values: bytearray | None = None
        self.height_prefix = b""
        self.height_header = b""
        self.objects: list[formats.MapObject] = []
        self.object_version = 0
        self.object_map_number = 0
        self.server_base: bytes | None = None
        self.server_values: bytearray | None = None
        self.server_map_number = tk.IntVar(value=0)
        self.server_baseline: bytearray | None = None
        self.attr_edited = bytearray(CELL_COUNT)
        self.attr_baseline: bytearray | None = None
        self.tile_colors = [(80, 80, 80)] * len(SLOT_NAMES)
        self.tile_images: list[Image.Image | None] = [None] * len(SLOT_NAMES)
        self.mode = tk.StringVar(value="Texture")
        self.layer = tk.IntVar(value=1)
        self.selected_tile = tk.IntVar(value=0)
        self.selected_attribute = tk.IntVar(value=4)
        self.brush = tk.IntVar(value=1)
        self.zoom = tk.IntVar(value=3)
        self.height_strength = tk.IntVar(value=4)
        self.show_grid = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="Open an EncTerrainN.map file to begin.")
        self._photo: ImageTk.PhotoImage | None = None
        self._stroke_active = False
        self._active_button = 1
        self._stroke_snapshot = None
        self._last_cell: tuple[int, int] | None = None
        self._object_selected: int | None = None
        self._object_dragging = False
        self._object_grab_offset = (0.0, 0.0)
        self.model_type = tk.IntVar(value=0)
        self.object_model_dir: Path | None = None
        self.object_models: dict[int, dict] = {}
        self.available_model_types: list[int] = []
        self.viewport3d = Viewport3D()
        self.view_mode = tk.StringVar(value="2D")
        self._orbit_last: tuple[int, int] | None = None
        self._build_ui()
        self.bind("<Control-o>", lambda _event: self.choose_folder())
        self.bind("<Control-s>", lambda _event: self.save_current())
        self.bind("<Control-z>", lambda _event: self.undo())

    def _build_ui(self) -> None:
        toolbar = ttk.Frame(self, padding=6)
        toolbar.pack(fill="x")
        ttk.Button(toolbar, text="Open map file…", command=self.choose_folder).pack(side="left")
        ttk.Button(toolbar, text="New map…", command=self.create_map_dialog).pack(side="left", padx=(5, 0))
        ttk.Label(toolbar, text="Map folder:").pack(side="left", padx=(12, 4))
        self.folder_label = ttk.Label(toolbar, text="(none)")
        self.folder_label.pack(side="left", fill="x", expand=True)
        ttk.Button(toolbar, text="Save current (Ctrl+S)", command=self.save_current).pack(side="right")
        ttk.Label(toolbar, text="View").pack(side="right", padx=(8, 3))
        view_box = ttk.Combobox(toolbar, textvariable=self.view_mode, values=("2D", "3D"), width=5, state="readonly")
        view_box.pack(side="right")
        view_box.bind("<<ComboboxSelected>>", lambda _e: self.render_map())

        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=6, pady=4)
        side = ttk.Frame(body, width=285, padding=6)
        work = ttk.Frame(body, padding=4)
        body.add(side, weight=0); body.add(work, weight=1)

        tabs = ttk.Notebook(side)
        tabs.pack(fill="both", expand=True)
        self.control_pages = {}
        for name in MODES:
            page = ttk.Frame(tabs, padding=8)
            tabs.add(page, text=name)
            self.control_pages[name] = page
        tabs.bind("<<NotebookTabChanged>>", self._tab_changed)
        self._build_texture_page(self.control_pages["Texture"])
        self._build_attribute_page(self.control_pages["Attribute"])
        self._build_height_page(self.control_pages["Height"])
        self._build_object_page(self.control_pages["Objects"])

        top = ttk.Frame(work)
        top.pack(fill="x", pady=(0, 5))
        ttk.Label(top, text="Zoom").pack(side="left")
        zoom_box = ttk.Combobox(top, textvariable=self.zoom, values=(2, 3, 4, 6, 8), width=5, state="readonly")
        zoom_box.pack(side="left", padx=5)
        zoom_box.bind("<<ComboboxSelected>>", lambda _e: self.render_map())
        ttk.Checkbutton(top, text="Grid", variable=self.show_grid, command=self.render_map).pack(side="left", padx=6)
        ttk.Label(top, text="2D: left paint · right lower / clear    3D: middle drag orbit · wheel zoom").pack(side="right")

        frame = ttk.Frame(work)
        frame.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(frame, background="#17191e", highlightthickness=0, cursor="crosshair")
        self.scroll_x = ttk.Scrollbar(frame, orient="horizontal", command=self.canvas.xview)
        self.scroll_y = ttk.Scrollbar(frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=self.scroll_x.set, yscrollcommand=self.scroll_y.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scroll_y.grid(row=0, column=1, sticky="ns")
        self.scroll_x.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1); frame.columnconfigure(0, weight=1)
        self.canvas.bind("<ButtonPress-1>", self._begin_stroke)
        self.canvas.bind("<B1-Motion>", self._paint_motion)
        self.canvas.bind("<ButtonRelease-1>", self._end_stroke)
        self.canvas.bind("<ButtonPress-3>", self._begin_stroke)
        self.canvas.bind("<B3-Motion>", self._paint_motion)
        self.canvas.bind("<ButtonRelease-3>", self._end_stroke)
        self.canvas.bind("<MouseWheel>", self._wheel)
        self.canvas.bind("<ButtonPress-2>", self._orbit_start)
        self.canvas.bind("<B2-Motion>", self._orbit_motion)
        self.canvas.bind("<ButtonRelease-2>", self._orbit_end)

        ttk.Label(self, textvariable=self.status, anchor="w", relief="sunken", padding=(6, 3)).pack(fill="x", side="bottom")

    def _section(self, parent: ttk.Frame, title: str) -> None:
        ttk.Label(parent, text=title, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(8, 4))
        ttk.Separator(parent).pack(fill="x", pady=(0, 5))

    def _build_texture_page(self, page: ttk.Frame) -> None:
        self._section(page, "Texture painting")
        for label, value in (("Layer 1 · base", 1), ("Layer 2 · overlay", 2)):
            ttk.Radiobutton(page, text=label, value=value, variable=self.layer, command=self.render_map).pack(anchor="w", pady=2)
        ttk.Label(page, text="Selected tile slot").pack(anchor="w", pady=(10, 3))
        self.palette = tk.Listbox(page, height=18, exportselection=False)
        self.palette.pack(fill="both", expand=True)
        self.palette.bind("<<ListboxSelect>>", self._palette_changed)
        ttk.Label(page, text="Layer 2 left paints opaque; right-click clears overlay.", wraplength=240).pack(anchor="w", pady=6)
        ttk.Button(page, text="Save terrain mapping (.map)", command=self.save_mapping).pack(fill="x", pady=3)

    def _build_attribute_page(self, page: ttk.Frame) -> None:
        self._section(page, "Walkability attributes")
        self.attr_buttons = []
        for label, value in ATTRIBUTES.items():
            button = ttk.Radiobutton(page, text=f"{label} ({value})", value=value, variable=self.selected_attribute)
            button.pack(anchor="w", pady=2); self.attr_buttons.append(button)
        ttk.Label(page, text="Brush radius").pack(anchor="w", pady=(12, 0))
        ttk.Spinbox(page, from_=1, to=20, textvariable=self.brush, width=8).pack(anchor="w")
        ttk.Button(page, text="Load server TerrainData…", command=self.load_server_base).pack(fill="x", pady=(12, 3))
        ttk.Button(page, text="Save client .att", command=self.save_attributes).pack(fill="x", pady=3)
        ttk.Label(page, text="Server map Number (world enum)").pack(anchor="w", pady=(8, 0))
        ttk.Spinbox(page, from_=0, to=255, textvariable=self.server_map_number, width=8).pack(anchor="w")
        ttk.Button(page, text="Export merged server .att…", command=self.export_server).pack(fill="x", pady=3)
        ttk.Label(page, text="Server export keeps all untouched server cells unchanged.", wraplength=240).pack(anchor="w", pady=7)

    def _build_height_page(self, page: ttk.Frame) -> None:
        self._section(page, "Terrain height")
        ttk.Label(page, text="Brush radius (tiles)").pack(anchor="w")
        ttk.Spinbox(page, from_=1, to=20, textvariable=self.brush, width=8).pack(anchor="w")
        ttk.Label(page, text="Strength (stored height steps)").pack(anchor="w", pady=(10, 0))
        ttk.Spinbox(page, from_=1, to=64, textvariable=self.height_strength, width=8).pack(anchor="w")
        ttk.Label(page, text="Left drag raises; right drag lowers.", wraplength=240).pack(anchor="w", pady=8)
        ttk.Button(page, text="Save terrain height (.OZB)", command=self.save_height).pack(fill="x", pady=3)

    def _build_object_page(self, page: ttk.Frame) -> None:
        self._section(page, "Map objects")
        self.object_tree = ttk.Treeview(page, columns=("type", "x", "y", "z", "ax", "ay", "az", "scale"), show="headings", height=14)
        for col, title, width in (("type", "Type", 48), ("x", "X", 55), ("y", "Y", 55), ("z", "Z", 55),
                                  ("ax", "Rot X", 52), ("ay", "Rot Y", 52), ("az", "Rot Z", 52), ("scale", "Scale", 55)):
            self.object_tree.heading(col, text=title); self.object_tree.column(col, width=width, anchor="center")
        self.object_tree.pack(fill="both", expand=True)
        self.object_tree.bind("<Double-1>", self._edit_object_cell)
        self.object_tree.bind("<<TreeviewSelect>>", self._object_row_selected)
        row = ttk.Frame(page); row.pack(fill="x", pady=6)
        ttk.Button(row, text="Add", command=self.add_object).pack(side="left", expand=True, fill="x")
        ttk.Button(row, text="Delete", command=self.delete_object).pack(side="left", expand=True, fill="x", padx=(5, 0))
        ttk.Button(page, text="Save objects (.obj)", command=self.save_objects).pack(fill="x", pady=3)
        ttk.Label(page, text="Model type to place").pack(anchor="w", pady=(8, 0))
        self.model_type_box = ttk.Combobox(page, textvariable=self.model_type, values=(), width=12, state="readonly")
        self.model_type_box.pack(anchor="w")
        ttk.Label(page, text="In 3D view: click empty ground to place; drag a model to move it. Double-click table values to edit transforms.", wraplength=240).pack(anchor="w", pady=5)

    def _tab_changed(self, _event=None) -> None:
        tabs = _event.widget if _event else None
        if tabs:
            name = tabs.tab(tabs.select(), "text")
            self.mode.set(name)
            self.render_map()

    def create_map_dialog(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("Create a blank MU map")
        dialog.transient(self)
        dialog.grab_set()
        frame = ttk.Frame(dialog, padding=12)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="New World folder number (WorldN)").grid(row=0, column=0, sticky="w")
        existing = set()
        if self.folder:
            existing = {int(p.name[5:]) for p in self.folder.parent.glob("World*") if p.name[5:].isdigit()}
        next_world = next((value for value in range(1, 256) if value not in existing), 1)
        number = tk.IntVar(value=next_world)
        ttk.Spinbox(frame, from_=1, to=255, textvariable=number, width=10).grid(row=0, column=1, sticky="w", padx=8)
        ttk.Label(frame, text="Template World folder").grid(row=1, column=0, sticky="w", pady=(10, 0))
        source = tk.StringVar(value=str(self.folder) if self.folder else "")
        ttk.Entry(frame, textvariable=source, width=56).grid(row=1, column=1, sticky="ew", padx=8, pady=(10, 0))
        ttk.Button(frame, text="Browse…", command=lambda: source.set(filedialog.askdirectory(parent=dialog) or source.get())).grid(row=1, column=2, pady=(10, 0))
        ttk.Label(frame, text="Target Data folder").grid(row=2, column=0, sticky="w", pady=(10, 0))
        data_root = tk.StringVar(value=str(self.folder.parent) if self.folder else "")
        ttk.Entry(frame, textvariable=data_root, width=56).grid(row=2, column=1, sticky="ew", padx=8, pady=(10, 0))
        ttk.Button(frame, text="Browse…", command=lambda: data_root.set(filedialog.askdirectory(parent=dialog) or data_root.get())).grid(row=2, column=2, pady=(10, 0))
        ttk.Label(frame, text="Creates blank map files and copies terrain textures. Client map registration is not changed.", wraplength=560).grid(row=3, column=0, columnspan=3, sticky="w", pady=10)
        def create() -> None:
            try:
                result = factory.create_blank_map(Path(data_root.get()), Path(source.get()), number.get())
            except (OSError, ValueError) as error:
                messagebox.showerror("Map creation failed", str(error), parent=dialog)
                return
            dialog.destroy()
            self.load_map_file(Path(result["world_folder"]) / f"EncTerrain{number.get()}.map")
            message = "New map files created. Register this world in the client before expecting it to load in game."
            if result["objects_copied"]:
                message += " The template model folder was copied too."
            messagebox.showinfo("Map created", message, parent=self)
        buttons = ttk.Frame(frame)
        buttons.grid(row=4, column=0, columnspan=3, sticky="e")
        ttk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side="right")
        ttk.Button(buttons, text="Create", command=create).pack(side="right", padx=6)
        frame.columnconfigure(1, weight=1)

    def choose_folder(self) -> None:
        selected = filedialog.askopenfilename(title="Choose EncTerrainN.map", filetypes=(("Terrain mapping", "EncTerrain*.map"), ("All files", "*.*")))
        if selected:
            self.load_map_file(Path(selected))

    def load_map_file(self, map_path: Path) -> None:
        folder = map_path.parent
        prefix = map_path.stem
        try:
            self.mapping = formats.read_mapping(map_path)
            att_path = folder / f"{prefix}.att"
            obj_path = folder / f"{prefix}.obj"
            height_path = folder / "TerrainHeight.OZB"
            self.attributes = formats.read_attributes(att_path) if att_path.exists() else None
            if obj_path.exists():
                self.object_version, self.object_map_number, self.objects = formats.read_objects(obj_path)
            else:
                self.objects = []; self.object_version = 0; self.object_map_number = self.mapping.map_number
            if height_path.exists():
                self.height_values, self.height_prefix, self.height_header = formats.read_height(height_path)
            else:
                self.height_values = None
        except (OSError, ValueError, struct.error) as error:
            messagebox.showerror("Could not open map", str(error))
            return
        self.folder = folder
        try:
            folder_number = int(folder.name.lower().removeprefix("world"))
            self.server_map_number.set(max(0, folder_number - 1))
        except ValueError:
            self.server_map_number.set(0)
        self.mapping_path = map_path
        self.attribute_path = att_path if att_path.exists() else None
        self.object_path = obj_path
        self.height_path = height_path if height_path.exists() else None
        self._load_object_models(folder)
        self.attr_edited = bytearray(CELL_COUNT)
        self.attr_baseline = bytearray(self.attributes.values) if self.attributes else None
        self.server_base = None; self.server_values = None; self.server_baseline = None
        self.folder_label.configure(text=str(folder))
        self._load_palette(folder)
        self._refresh_objects()
        missing = [name for name, exists in ((".att", self.attributes is not None), ("height", self.height_values is not None)) if not exists]
        self.status.set(f"Loaded {map_path.name}: 256×256, {len(self.objects)} objects" + (f" · missing {', '.join(missing)}" if missing else ""))
        self.render_map()

    def _load_object_models(self, folder: Path) -> None:
        suffix = folder.name.lower().removeprefix("world")
        if not suffix.isdigit():
            self.object_model_dir = None
            self.available_model_types = []
            self.object_models.clear()
            return
        self.object_model_dir = folder.parent / f"Object{suffix}"
        self.available_model_types = sorted(
            int(p.stem[len("Object"):]) - 1 for p in self.object_model_dir.glob("Object*.bmd")
            if p.stem[len("Object"):].isdigit() and int(p.stem[len("Object"):]) > 0
        ) if self.object_model_dir.is_dir() else []
        self.object_models.clear()
        if hasattr(self, "model_type_box"):
            self.model_type_box.configure(values=tuple(self.available_model_types))
            if self.available_model_types and self.model_type.get() not in self.available_model_types:
                self.model_type.set(self.available_model_types[0])

    def _get_object_model(self, type_id: int):
        if type_id in self.object_models:
            return self.object_models[type_id]
        if self.object_model_dir is None:
            return None
        model_path = self.object_model_dir / f"Object{type_id + 1}.bmd"
        if not model_path.is_file():
            return None
        scripts = Path(__file__).resolve().parents[2] / ".agents" / "skills" / "mu-art-pipeline" / "scripts"
        if str(scripts) not in sys.path:
            sys.path.insert(0, str(scripts))
        try:
            from mu_art_pipeline.bmd import parse_bmd
            model = parse_bmd(model_path)
            for mesh in model.get("meshes", []):
                texture = mesh.get("texture", "")
                texture_path = next((candidate for extension in (".OZJ", ".OZT", ".jpg", ".tga")
                                     if (candidate := self.object_model_dir / f"{texture}{extension}").is_file()), None)
                preview = image_from_resource(texture_path) if texture_path else None
                mesh["preview_color"] = preview.resize((1, 1)).getpixel((0, 0)) if preview else (158, 143, 105)
            self.object_models[type_id] = model
            return model
        except (OSError, ValueError, struct.error):
            return None

    def _load_palette(self, folder: Path) -> None:
        self.palette.delete(0, "end")
        for slot, name in enumerate(SLOT_NAMES):
            candidates = ([folder / f"{name}.OZJ", folder / f"{name}.OZT", folder / f"{name}.jpg", folder / f"{name}.tga"])
            image = next((img for p in candidates if (img := image_from_resource(p)) is not None), None)
            self.tile_images[slot] = image
            if slot < 14:
                self.tile_colors[slot] = image.resize((1, 1)).getpixel((0, 0)) if image else (75, 75, 75)
            else:
                self.tile_colors[slot] = image.resize((1, 1)).getpixel((0, 0)) if image else (42, 70, 98)
            state = name if image else f"{name} (empty)"
            self.palette.insert("end", f"{slot:02d}  {state}")
            r, g, b = self.tile_colors[slot]
            foreground = "#111111" if r + g + b > 390 else "#f4f4f4"
            self.palette.itemconfig(slot, background=f"#{r:02x}{g:02x}{b:02x}", foreground=foreground)
        if self.mapping:
            self.selected_tile.set(min(self.selected_tile.get(), 29))
            self.palette.selection_set(self.selected_tile.get())

    def _palette_changed(self, _event=None) -> None:
        selection = self.palette.curselection()
        if selection:
            self.selected_tile.set(selection[0]); self.render_map()

    def _tab_name(self) -> str:
        return self.mode.get()

    def _cell_color(self, index: int, mode: str) -> tuple[int, int, int]:
        if mode == "Attribute" and self.attributes:
            value = self.attributes.values[index] & ~0x02
            if value & 8: return ATTR_COLORS[8]
            if value & 4: return ATTR_COLORS[4]
            if value & 16: return ATTR_COLORS[16]
            if value & 1: return ATTR_COLORS[1]
            return ATTR_COLORS[0]
        if mode == "Height" and self.height_values is not None:
            level = self.height_values[index]
            return (level, level, level)
        if mode == "Objects":
            return self.tile_colors[self.mapping.layer1[index] % len(self.tile_colors)] if self.mapping else (45, 50, 58)
        if not self.mapping:
            return (45, 50, 58)
        slot1 = self.mapping.layer1[index] % len(self.tile_colors)
        color = self.tile_colors[slot1]
        if self.layer.get() == 2:
            slot2 = self.mapping.layer2[index] % len(self.tile_colors)
            alpha = self.mapping.alpha[index] / 255
            overlay = self.tile_colors[slot2]
            color = tuple(round(color[c] * (1 - alpha) + overlay[c] * alpha) for c in range(3))
        return color

    def render_map(self) -> None:
        if not hasattr(self, "canvas"):
            return
        self.canvas.delete("all")
        if self.view_mode.get() == "3D" and self.mapping is not None:
            width = max(800, self.canvas.winfo_width())
            height = max(600, self.canvas.winfo_height())
            height_values = self.height_values if self.height_values is not None else bytearray(CELL_COUNT)
            for type_id in {obj.type_id for obj in self.objects}:
                self._get_object_model(type_id)
            image = self.viewport3d.render(width, height, self.mapping, height_values,
                                           self.tile_colors, self.objects, self.object_models,
                                           self.mode.get(), self.attributes.values if self.attributes else None)
            self._photo = ImageTk.PhotoImage(image)
            self.canvas.create_image(0, 0, image=self._photo, anchor="nw")
            self.canvas.configure(scrollregion=(0, 0, image.width, image.height))
            return
        zoom = max(1, int(self.zoom.get()))
        mode = self._tab_name()
        image = Image.new("RGB", (256, 256))
        pixels = image.load()
        for index in range(CELL_COUNT):
            x, y = index % 256, index // 256
            pixels[x, y] = self._cell_color(index, mode)
        if self.show_grid.get() and zoom >= 3:
            draw = ImageDraw.Draw(image)
            for x in range(0, 256, 16): draw.line((x, 0, x, 255), fill=(18, 20, 23))
            for y in range(0, 256, 16): draw.line((0, y, 255, y), fill=(18, 20, 23))
        image = image.resize((256 * zoom, 256 * zoom), Image.Resampling.NEAREST)
        self._photo = ImageTk.PhotoImage(image)
        self.canvas.create_image(0, 0, image=self._photo, anchor="nw")
        self.canvas.configure(scrollregion=(0, 0, image.width, image.height))
        self._draw_objects()

    def _draw_objects(self) -> None:
        if self.mode.get() != "Objects" or not self.objects:
            return
        zoom = int(self.zoom.get())
        for i, obj in enumerate(self.objects):
            cx, cy = int(obj.x / 100 * zoom), int(obj.y / 100 * zoom)
            color = "#fff06a" if i == self._object_selected else "#e7ebf1"
            self.canvas.create_oval(cx-3, cy-3, cx+3, cy+3, fill=color, outline="#17191e", tags=(f"object-{i}",))

    def _canvas_cell(self, event) -> tuple[int, int] | None:
        x = int(self.canvas.canvasx(event.x) // int(self.zoom.get()))
        y = int(self.canvas.canvasy(event.y) // int(self.zoom.get()))
        if not (0 <= x < 256 and 0 <= y < 256): return None
        return x, y

    def _begin_stroke(self, event) -> None:
        if self.view_mode.get() == "3D":
            cell = self.viewport3d.pick_cell(self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
            if cell is None:
                return
            if self.mode.get() == "Objects" and event.num == 1:
                object_index = self.viewport3d.pick_object(self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
                if object_index is not None:
                    self._object_selected = object_index
                    self.object_tree.selection_set(str(object_index))
                    obj = self.objects[object_index]
                    self._object_grab_offset = (obj.x - cell[0] * 100.0, obj.y - cell[1] * 100.0)
                    self._object_dragging = True
                    self.render_map()
                    return
                z = self.height_values[cell[1] * 256 + cell[0]] * 1.5 if self.height_values else 0.0
                obj = formats.MapObject(self.model_type.get(), cell[0] * 100.0, cell[1] * 100.0,
                                        z, 0.0, 0.0, 0.0, 1.0)
                self.objects.append(obj)
                self._object_selected = len(self.objects) - 1
                self._refresh_objects()
                self.object_tree.selection_set(str(self._object_selected))
                self._object_dragging = True
                self._object_grab_offset = (0.0, 0.0)
                self.render_map()
                return
            if self.folder is None:
                return
            self._stroke_snapshot = self._snapshot()
            self._stroke_active = True
            self._active_button = event.num
            self._last_cell = None
            self._paint_cell(cell, event.num)
            return
        cell = self._canvas_cell(event)
        if cell is None or self.folder is None: return
        self._stroke_snapshot = self._snapshot()
        self._stroke_active = True
        self._active_button = event.num
        self._last_cell = None
        self._paint_cell(cell, self._active_button)

    def _paint_motion(self, event) -> None:
        if self.view_mode.get() == "3D" and self._object_dragging and self._object_selected is not None:
            cell = self.viewport3d.pick_cell(self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
            if cell:
                obj = self.objects[self._object_selected]
                obj.x = max(0.0, min(25500.0, cell[0] * 100.0 + self._object_grab_offset[0]))
                obj.y = max(0.0, min(25500.0, cell[1] * 100.0 + self._object_grab_offset[1]))
                if self.height_values is not None:
                    obj.z = self.height_values[cell[1] * 256 + cell[0]] * 1.5
                self._refresh_objects()
                self.object_tree.selection_set(str(self._object_selected))
                self.render_map()
            return
        if not self._stroke_active: return
        cell = (self.viewport3d.pick_cell(self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)) if self.view_mode.get() == "3D"
                else self._canvas_cell(event))
        if cell is not None: self._paint_cell(cell, self._active_button)

    def _end_stroke(self, _event=None) -> None:
        self._stroke_active = False
        self._object_dragging = False
        self._last_cell = None

    def _orbit_start(self, event) -> None:
        if self.view_mode.get() == "3D":
            self._orbit_last = (event.x, event.y)

    def _orbit_motion(self, event) -> None:
        if self.view_mode.get() != "3D" or self._orbit_last is None:
            return
        x, y = self._orbit_last
        self.viewport3d.orbit(event.x - x, event.y - y)
        self._orbit_last = (event.x, event.y)
        self.render_map()

    def _orbit_end(self, _event=None) -> None:
        self._orbit_last = None

    def _snapshot(self):
        if self.mode.get() == "Texture" and self.mapping:
            return ("Texture", bytearray(self.mapping.layer1), bytearray(self.mapping.layer2), bytearray(self.mapping.alpha))
        if self.mode.get() == "Attribute" and self.attributes:
            return ("Attribute", bytearray(self.attributes.values), bytearray(self.attr_edited))
        if self.mode.get() == "Height" and self.height_values is not None:
            return ("Height", bytearray(self.height_values))
        return None

    def undo(self) -> None:
        snap = self._stroke_snapshot
        if not snap: return
        if snap[0] == "Texture" and self.mapping:
            self.mapping.layer1, self.mapping.layer2, self.mapping.alpha = snap[1:]
        elif snap[0] == "Attribute" and self.attributes:
            self.attributes.values, self.attr_edited = snap[1:]
        elif snap[0] == "Height":
            self.height_values = snap[1]
        self._stroke_snapshot = None
        self.status.set("Undid the last painting stroke.")
        self.render_map()

    def _paint_cell(self, cell: tuple[int, int], button: int) -> None:
        x, y = cell
        if cell == self._last_cell: return
        self._last_cell = cell
        radius = max(1, int(self.brush.get())) - 1
        mode = self.mode.get()
        if mode == "Objects":
            nearest = min(range(len(self.objects)), key=lambda i: (self.objects[i].x/100-x)**2 + (self.objects[i].y/100-y)**2, default=None)
            self._object_selected = nearest
            self._refresh_objects()
            if nearest is not None: self.object_tree.selection_set(str(nearest))
            self.render_map()
            return
        if mode == "Attribute" and not self.attributes: return
        if mode == "Height" and self.height_values is None: return
        if mode == "Texture" and self.mapping is None: return
        for cy in range(max(0, y-radius), min(255, y+radius)+1):
            for cx in range(max(0, x-radius), min(255, x+radius)+1):
                if (cx-x)**2 + (cy-y)**2 > radius**2: continue
                index = cy*256+cx
                if mode == "Texture":
                    if self.layer.get() == 1:
                        self.mapping.layer1[index] = self.selected_tile.get()
                    elif button == 1:
                        self.mapping.layer2[index] = self.selected_tile.get(); self.mapping.alpha[index] = 255
                    else:
                        self.mapping.alpha[index] = 0
                elif mode == "Attribute":
                    value = 0 if button == 3 else self.selected_attribute.get()
                    self.attributes.values[index] = value
                    self.attr_edited[index] = 1
                elif mode == "Height":
                    change = int(self.height_strength.get()) * (1 if button == 1 else -1)
                    self.height_values[index] = max(0, min(255, self.height_values[index] + change))
        self.render_map()

    def _wheel(self, event) -> None:
        if self.view_mode.get() == "3D":
            self.viewport3d.zoom(event.delta)
            self.render_map()
            return
        values = (2, 3, 4, 6, 8)
        current = values.index(self.zoom.get()) if self.zoom.get() in values else 1
        next_index = max(0, min(len(values)-1, current + (1 if event.delta > 0 else -1)))
        self.zoom.set(values[next_index]); self.render_map()

    def save_current(self) -> None:
        mode = self.mode.get()
        if mode == "Texture": self.save_mapping()
        elif mode == "Attribute": self.save_attributes()
        elif mode == "Height": self.save_height()
        else: self.save_objects()

    def _save_with_backup(self, path: Path, writer) -> None:
        backup = path.with_suffix(path.suffix + ".bak")
        try:
            if path.exists() and not backup.exists():
                backup.write_bytes(path.read_bytes())
            writer()
            self.status.set(f"Saved {path.name} · backup: {backup.name if backup.exists() else 'none'}")
        except (OSError, ValueError, struct.error) as error:
            messagebox.showerror("Save failed", str(error))

    def save_mapping(self) -> None:
        path = self.mapping_path if self.mapping else None
        if path and self.mapping: self._save_with_backup(path, lambda: formats.write_mapping(path, self.mapping))

    def save_attributes(self) -> None:
        path = self.attribute_path if self.attributes else None
        if path and self.attributes: self._save_with_backup(path, lambda: formats.write_attributes(path, self.attributes))

    def save_height(self) -> None:
        path = self.height_path
        if path and self.height_values is not None:
            self._save_with_backup(path, lambda: formats.write_height(path, self.height_values, self.height_prefix, self.height_header))

    def save_objects(self) -> None:
        path = self.object_path
        if path: self._save_with_backup(path, lambda: formats.write_objects(path, self.object_version, self.object_map_number, self.objects))

    def load_server_base(self) -> None:
        selected = filedialog.askopenfilename(title="Choose server TerrainData downloaded from Admin Panel", filetypes=(("Terrain data", "*.att"), ("All files", "*.*")))
        if not selected: return
        try:
            self.server_base = Path(selected).read_bytes()
            _header, self.server_values = formats.read_server_attributes(Path(selected))
        except (OSError, ValueError) as error:
            self.server_base = None; self.server_values = None
            messagebox.showerror("Invalid server TerrainData", str(error)); return
        self.server_baseline = bytearray(self.attr_baseline) if self.attr_baseline else bytearray(CELL_COUNT)
        self.status.set(f"Loaded server TerrainData base · map Number is the world enum, not the World folder number.")

    def export_server(self) -> None:
        if self.server_base is None or self.attributes is None or self.server_baseline is None:
            messagebox.showinfo("Server export", "Load the server TerrainData base first, and open a map with EncTerrainN.att.")
            return
        path = filedialog.asksaveasfilename(title="Export merged server TerrainData", initialfile=f"terrain_map{self.server_map_number.get()}_server.att", defaultextension=".att")
        if not path: return
        try:
            changed = formats.write_server_attributes(Path(path), self.server_base, self.attributes.values,
                                                       self.server_baseline, self.attr_edited)
            self.status.set(f"Exported merged server .att · {changed} changed tiles")
        except (OSError, ValueError) as error:
            messagebox.showerror("Export failed", str(error))

    def _refresh_objects(self) -> None:
        if not hasattr(self, "object_tree"): return
        self.object_tree.delete(*self.object_tree.get_children())
        for i, obj in enumerate(self.objects):
            values = (obj.type_id, f"{obj.x:.2f}", f"{obj.y:.2f}", f"{obj.z:.2f}",
                      f"{obj.angle_x:.2f}", f"{obj.angle_y:.2f}", f"{obj.angle_z:.2f}", f"{obj.scale:.3f}")
            self.object_tree.insert("", "end", iid=str(i), values=values)

    def _edit_object_cell(self, event) -> None:
        row = self.object_tree.identify_row(event.y); col = self.object_tree.identify_column(event.x)
        if not row or col == "#0": return
        index = int(row); column_index = int(col[1:]) - 1
        box = self.object_tree.bbox(row, col)
        if not box: return
        entry = ttk.Entry(self.object_tree)
        entry.place(x=box[0], y=box[1], width=box[2], height=box[3])
        entry.insert(0, self.object_tree.set(row, col)); entry.focus_set()
        def commit(_event=None):
            if not entry.winfo_exists(): return
            try:
                value = float(entry.get())
                if column_index == 0: value = int(value)
                obj = self.objects[index]
                fields = ["type_id", "x", "y", "z", "angle_x", "angle_y", "angle_z", "scale"]
                setattr(obj, fields[column_index], value)
                self._refresh_objects(); self.render_map()
            except (ValueError, IndexError):
                messagebox.showerror("Invalid value", "Enter a valid number.")
            entry.destroy()
        entry.bind("<Return>", commit); entry.bind("<FocusOut>", commit)

    def _object_row_selected(self, _event=None) -> None:
        selected = self.object_tree.selection()
        self._object_selected = int(selected[0]) if selected else None
        self.render_map()

    def add_object(self) -> None:
        self.objects.append(formats.MapObject(0, 12800.0, 12800.0, 0.0, 0.0, 0.0, 0.0, 1.0))
        self._refresh_objects(); self.render_map()
        self.status.set("Added object at map center; edit coordinates and Type in the table.")

    def delete_object(self) -> None:
        selected = self.object_tree.selection()
        if not selected: return
        del self.objects[int(selected[0])]
        self._object_selected = None; self._refresh_objects(); self.render_map()


def main() -> None:
    app = MapEditor()
    app.mainloop()


if __name__ == "__main__":
    main()
