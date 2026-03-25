# MicroGallery — Invariants

These constraints must never be violated without explicit user approval and a devlog entry.

---

## 1. Image-to-cell assignment rule

Images in a folder are sorted **alphabetically by filename (case-insensitive)** and assigned
to non-empty layout cells in **row-major order** (left-to-right, top-to-bottom).

- Empty layout cells (blank value in the Excel/CSV) are **blank slots** — they consume no image.
- If there are more labeled cells than images, extra cells render with their label but no image.
- If there are more images than labeled cells, the excess images are silently ignored.

This rule is the contract between the user's file-naming conventions and the output grid.
Any change to it will silently reorder every grid the user has ever built.

**Location:** `renderer.assign_cells()` and `renderer.scan_images()`

---

## 2. renderer.py has no Streamlit dependency

`renderer.py` must never import `streamlit`. It is a pure image-processing library.
This makes it independently testable and reusable outside Streamlit.

---

## 3. Layout file defines grid structure completely

The shape of the layout file (rows × columns) defines the output grid.
There is no manual column/row override in the UI. The layout file is the single source
of truth for grid dimensions.

---

## 4. One layout file per session

All folders in the batch share the same layout file. Per-folder layouts are not supported.
If different layouts are needed, open a separate app instance.

---

## 5. Supported image formats

`{".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}`

Changes to this set affect which files are picked up from folders — verify alphabetical
sort behaviour is preserved after any change.

---

## 6. 16-bit TIFF handling

Images with PIL mode `I;16` are converted to 8-bit RGB via `pixel / 256`.
This is the correct linear conversion for microscopy images from Keyence.
Do not change the conversion formula without user confirmation.
