# MicroGallery

A Streamlit web app for building labeled image gallery grids from microscopy image folders.
Designed for High-Throughput Screening (HTS) workflows on the Keyence microscope platform.

> Documentation written by [Claude](https://claude.ai) (Anthropic).

---

## What it does

MicroGallery takes a folder of images and a layout file (Excel or CSV), and renders a labeled PNG grid where each cell shows one image with its label overlaid. Multiple folders can be processed in one batch — each produces its own gallery PNG saved automatically next to the source folder.

**Before MicroGallery:** two CLI scripts had to be run in sequence — one to scan folders and generate a manifest (`BE.xlsx`), then another to read the manifest and render the grid.

**After MicroGallery:** one web UI, no intermediate files.

---

## Quick start

### Requirements

- Python 3.10+
- Windows (the Browse dialog uses `tkinter`; the app otherwise runs on any OS)

### Installation

```bash
cd microgallery
python -m venv venv
venv\Scripts\activate       # PowerShell: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Run

Double-click `run.bat`, or:

```bash
streamlit run app.py
```

The app opens in your browser at `http://localhost:8501`.

---

## Workflow

### 1. Add image folders

Click **Browse** to open a native OS folder picker — the folder is added to the batch list immediately. Or paste a path into the text box and click **Add**.

Repeat for each folder. All folders in the list will use the same layout file.

### 2. Upload a layout file

Upload a `.csv`, `.xlsx`, or `.xls` file that defines the grid structure:

- Rows and columns define the grid dimensions.
- Filled cells contain the label text for that position.
- Empty cells become blank slots (no image rendered there).

**Example layout (4 × 3 grid):**

| | | | |
|---|---|---|---|
| DMSO | Compound A | Compound B | Compound C |
| 1 µM | 1 µM | 1 µM | 1 µM |
| 10 µM | 10 µM | 10 µM | 10 µM |

### 3. Tune label style

The controls bar has three groups:

| Group | Controls |
|-------|----------|
| **Label Style** | Font % (relative to cell height), Label height (px), Padding (px) |
| **Colors** | Label BG checkbox + color, Text color |
| **Display** | Preview zoom % |

The **Preview** panel (bottom right) updates live as you adjust settings, showing the first image from the first folder.

### 4. Build

Click **Build Gallery** (or **Build N Galleries** for a batch). Each gallery PNG is saved automatically to:

```
<parent of source folder>/<folder name>_gallery.png
```

For example, `C:\Data\Plate01\` → `C:\Data\Plate01_gallery.png`.

### 5. Settings save / load

- Click **Save Settings** (in the Settings column) to download a JSON file containing all current label style settings and the layout grid labels.
- Upload a saved `.json` file in the Settings column to restore a previous configuration — including the label grid, so you don't need to re-upload the layout Excel.

---

## Image-to-cell assignment rule

Images in a folder are sorted **alphabetically by filename (case-insensitive)** and assigned to non-empty layout cells in **row-major order** (left-to-right, top-to-bottom).

- Empty layout cells consume no image — they render as blank white space.
- If there are more labeled cells than images, extra cells render with label text but no image.
- If there are more images than labeled cells, the excess images are silently ignored.

A mismatch warning is shown in the Layout panel for each folder.

---

## Supported image formats

`.png` `.jpg` `.jpeg` `.tif` `.tiff` `.bmp`

16-bit TIFF files (Keyence output) are automatically converted to 8-bit RGB using a linear scale (`pixel / 256`).

---

## File structure

```
microgallery/
├── app.py            # Streamlit UI — all session state and widgets
├── renderer.py       # Pure image processing library (no Streamlit dependency)
├── requirements.txt  # Python dependencies
├── run.bat           # Windows double-click launcher
└── README.md
```

### `app.py`

Owns all Streamlit session state and UI layout. Key sections:

- **Row 1** — Image Folders | Layout File | Settings (inputs)
- **Controls bar** — Label Style | Colors | Display (tuning)
- **Build button** — triggers batch render and auto-save
- **Bottom panel** — editable Layout grid (`st.data_editor`) + live Preview tile

Session state keys are defined as module-level constants (`_FOLDERS`, `_LAYOUT`, etc.) and initialized via `_init_state()`. Settings are assembled for renderer calls by `_current_settings()`.

### `renderer.py`

Pure Python image processing — zero Streamlit imports. Can be used independently of the web UI.

| Function | Description |
|----------|-------------|
| `load_layout(file)` | Parse CSV/Excel → string DataFrame |
| `scan_images(folder)` | List images in folder, alphabetical sort |
| `assign_cells(layout, images)` | Pair images with labeled cells, row-major |
| `count_labeled_cells(layout)` | Count non-empty cells in layout |
| `get_cell_dimensions(images)` | Max width/height across image set |
| `render_gallery(folder, layout, settings)` | Render full grid → PIL Image |
| `render_preview(folder, layout, settings)` | Render first tile → PIL Image |
| `to_png(image)` | PIL Image → PNG bytes |
| `to_zip(entries)` | List of (name, bytes) → ZIP bytes |

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `streamlit >= 1.32` | Web UI framework |
| `pandas >= 2.0` | Layout file parsing and editing |
| `Pillow >= 10.0` | Image loading, resizing, compositing |
| `openpyxl >= 3.1` | `.xlsx` support |
| `xlrd >= 2.0` | `.xls` support |

---

## Known limitations

- All folders in a batch share one layout file. For different layouts, open a second app instance.
- Output path is fixed to `<folder parent>/<folder name>_gallery.png`. There is no UI override for save location.
- The Browse dialog requires a local desktop environment (not a remote headless server).

---

*Documentation written by [Claude Sonnet 4.6](https://claude.ai) (Anthropic).*
