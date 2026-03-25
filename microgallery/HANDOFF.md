# MicroGallery — Handoff

_Update this file at the end of every session._

---

## Session: 2026-03-24 (continued)

### What was completed
- Built the entire app from scratch (`app.py`, `renderer.py`, `requirements.txt`, `run.bat`)
- Replaced the two-step CLI pipeline (getbe → image_merger) with a single Streamlit web UI
- Confirmed working end-to-end: Browse folder, upload layout, preview, Build, auto-save PNG
- Fixed `number_input` initialization bug (Preview % jumping to 15 on first click)
- Fixed `StreamlitAPIException` from setting a widget key after render (Browse button)
- Made Browse auto-add folder to batch list (removed the extra Add step)
- Created `CLAUDE.md`, `docs/invariants.md`, `docs/devlog.md`, `HANDOFF.md`
- Added layout editor (`st.data_editor`), settings save/load (JSON), controls redesign, Build moved to top of controls area
- Removed download buttons — build auto-saves PNG next to source folder
- Settings/layout filename display: loaded filenames shown in folder-list style (caption + ✕ button) in layout and settings columns
- Controls restructured into 3-row layout: group labels (Label BG toggle alongside "Colors" header) | pickers and number inputs | full-width Build Gallery button below

### Current state

**Working:**
- Folder Browse (native OS dialog, auto-adds to batch list)
- Manual folder path entry + Add button
- Batch list with per-folder remove
- Layout file upload (CSV, XLS, XLSX)
- Live preview tile (updates on every settings change)
- Label style controls: Font %, Label height, Padding, Label BG toggle + color, Text color
- Preview zoom
- Per-folder image/cell mismatch warning in layout panel
- Build gallery — single folder or batch
- Download PNG (single) and Download ZIP (batch)
- 16-bit TIFF support
- `run.bat` double-click launcher

**Not yet implemented:**
- Image sort preview (no way to see the alphabetical filename order before building)
- Per-folder output path selection (saves next to source folder; no UI override)

### Open questions
- Is alphabetical filename sort always correct for the user's naming conventions?
- Should Preview show the full first-row strip rather than just one tile?

### Recommended next steps (priority order)
1. **Image order preview** — show the sorted filename list alongside the layout so user can verify mapping before building.
2. **Output path override** — let user choose where the gallery PNG is saved (currently hardcoded to `parent / name + "_gallery.png"`).
