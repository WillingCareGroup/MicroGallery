"""
renderer.py — pure image processing for MicroGallery.
No Streamlit dependency; all functions take plain Python types.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Optional

import pandas as pd
from PIL import Image, ImageColor, ImageDraw, ImageFont

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}


# ─── Image utilities ──────────────────────────────────────────────────────────

def _normalize(image: Image.Image) -> Image.Image:
    """Convert any PIL mode to 8-bit RGB."""
    if image.mode == "I;16":
        return image.point(lambda v: v / 256).convert("RGB")
    if image.mode != "RGB":
        return image.convert("RGB")
    return image.copy()


def _load_font(size: int) -> ImageFont.ImageFont:
    for name in ("arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"):
        try:
            return ImageFont.truetype(name, max(10, size))
        except OSError:
            continue
    return ImageFont.load_default()


def _fit(image: Image.Image, w: int, h: int) -> Image.Image:
    """Scale image to fit within (w, h) preserving aspect ratio."""
    scale = min(w / image.width, h / image.height)
    return image.resize(
        (max(1, int(image.width * scale)), max(1, int(image.height * scale))),
        Image.LANCZOS,
    )


def _draw_label(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    cw: int,
    ch: int,
    label: str,
    font: ImageFont.ImageFont,
    text_rgb: tuple,
    label_h: int,
    padding: int,
    bg_hex: str,
) -> None:
    if not label:
        return
    bb = draw.textbbox((0, 0), label, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    bw = tw + padding * 2
    bh = max(label_h, th + max(2, padding))
    bx = cx + max(0, (cw - bw) // 2)
    by = cy + padding
    if bg_hex:
        bg = ImageColor.getrgb(bg_hex) + (170,)
        draw.rounded_rectangle((bx, by, bx + bw, by + bh), radius=8, fill=bg)
    tx = bx + (bw - tw) // 2
    ty = by + (bh - th) // 2
    # black outline for legibility
    for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        draw.text((tx + dx, ty + dy), label, font=font, fill=(0, 0, 0))
    draw.text((tx, ty), label, font=font, fill=text_rgb)


# ─── Layout parsing ───────────────────────────────────────────────────────────

def load_layout(file) -> pd.DataFrame:
    """
    Parse a CSV or Excel layout file into a string DataFrame.
    Each cell value is the label for that grid position; empty = blank slot.
    """
    name = getattr(file, "name", str(file))
    ext = Path(name).suffix.lower()
    if ext == ".csv":
        df = pd.read_csv(file, header=None)
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(file, header=None)
    else:
        raise ValueError(f"Unsupported layout format '{ext}'. Use .csv, .xlsx, or .xls.")
    return df.fillna("").astype(str).apply(lambda col: col.str.strip())


# ─── Folder scanning ─────────────────────────────────────────────────────────

def scan_images(folder: str) -> list[Path]:
    """Return image paths in folder, sorted alphabetically by filename."""
    p = Path(folder)
    imgs = [f for f in p.iterdir() if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS]
    return sorted(imgs, key=lambda f: f.name.lower())


# ─── Cell assignment ─────────────────────────────────────────────────────────

def assign_cells(layout: pd.DataFrame, images: list[Path]) -> list[tuple[Optional[Path], str]]:
    """
    Pair images with non-empty layout cells in row-major order.
    Empty layout cells become (None, "") — blank slots in the output grid.
    If there are more labeled cells than images, extra cells get (None, label).
    """
    it = iter(images)
    cells: list[tuple[Optional[Path], str]] = []
    for r in range(layout.shape[0]):
        for c in range(layout.shape[1]):
            label = layout.iat[r, c]
            cells.append((next(it, None) if label else None, label))
    return cells


def count_labeled_cells(layout: pd.DataFrame) -> int:
    return sum(1 for r in range(layout.shape[0]) for c in range(layout.shape[1]) if layout.iat[r, c])


# ─── Dimension helpers ────────────────────────────────────────────────────────

def get_cell_dimensions(images: list[Path]) -> tuple[int, int]:
    """
    Read image dimensions without fully decoding pixel data.
    Returns (max_width, max_height) across all images.
    """
    if not images:
        raise ValueError("No images to measure.")
    max_w = max_h = 0
    for path in images:
        with Image.open(path) as img:
            w, h = img.size
            max_w, max_h = max(max_w, w), max(max_h, h)
    return max_w, max_h


# ─── Rendering ────────────────────────────────────────────────────────────────

def render_gallery(folder: str, layout: pd.DataFrame, settings: dict) -> Image.Image:
    """
    Render the full image grid for a folder.
    settings keys: font_scale (int %), label_h (int px), padding (int px),
                   label_bg_on (bool), label_bg (hex str), text_color (hex str)
    """
    images = scan_images(folder)
    cells = assign_cells(layout, images)

    assigned_images = [p for p, _ in cells if p is not None]
    if not assigned_images:
        raise ValueError(f"No images were assigned from '{Path(folder).name}'. "
                         "Check that the folder contains images and the layout has labeled cells.")

    cell_w, cell_h = get_cell_dimensions(assigned_images)
    cols = layout.shape[1]
    rows = layout.shape[0]

    font = _load_font(max(10, int(cell_h * settings["font_scale"] / 100)))
    text_rgb = ImageColor.getrgb(settings["text_color"])
    bg_hex = settings["label_bg"] if settings["label_bg_on"] else ""

    canvas = Image.new("RGB", (cell_w * cols, cell_h * rows), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    for i, (path, label) in enumerate(cells):
        row, col = divmod(i, cols)
        cx, cy = col * cell_w, row * cell_h
        if path is not None:
            with Image.open(path) as img:
                src = _normalize(img)
            fitted = _fit(src, cell_w, cell_h)
            canvas.paste(fitted, (cx + (cell_w - fitted.width) // 2,
                                  cy + (cell_h - fitted.height) // 2))
        if label:
            _draw_label(draw, cx, cy, cell_w, cell_h, label,
                        font, text_rgb, settings["label_h"], settings["padding"], bg_hex)

    return canvas


def render_preview(folder: str, layout: pd.DataFrame, settings: dict) -> tuple[Image.Image, int, int]:
    """
    Render the first assigned cell as a style preview tile.
    Returns (tile_image, cell_w, cell_h).
    """
    images = scan_images(folder)
    cells = assign_cells(layout, images)

    assigned_images = [p for p, _ in cells if p is not None]
    if not assigned_images:
        raise ValueError("No images assigned to any layout cell.")

    cell_w, cell_h = get_cell_dimensions(assigned_images)

    first_path, first_label = next(((p, l) for p, l in cells if p is not None), (None, ""))
    if first_path is None:
        raise ValueError("No images to preview.")

    font = _load_font(max(10, int(cell_h * settings["font_scale"] / 100)))
    text_rgb = ImageColor.getrgb(settings["text_color"])
    bg_hex = settings["label_bg"] if settings["label_bg_on"] else ""

    canvas = Image.new("RGB", (cell_w, cell_h), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    with Image.open(first_path) as img:
        src = _normalize(img)
    fitted = _fit(src, cell_w, cell_h)
    canvas.paste(fitted, ((cell_w - fitted.width) // 2, (cell_h - fitted.height) // 2))

    _draw_label(draw, 0, 0, cell_w, cell_h, first_label,
                font, text_rgb, settings["label_h"], settings["padding"], bg_hex)

    return canvas, cell_w, cell_h


# ─── Export ───────────────────────────────────────────────────────────────────

def to_png(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG", optimize=False, compress_level=1)
    return buf.getvalue()


def to_zip(entries: list[tuple[str, bytes]]) -> bytes:
    """Bundle (filename, png_bytes) pairs into a ZIP archive."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries:
            zf.writestr(name, data)
    return buf.getvalue()
