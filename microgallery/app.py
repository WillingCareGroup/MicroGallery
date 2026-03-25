"""
app.py — MicroGallery Streamlit web UI.

Workflow:
  1. Add one or more image folders (Browse auto-adds, or type path + Add).
  2. Upload a layout file (.csv / .xlsx / .xls) that defines the grid and labels.
  3. Optionally load a settings file to restore a previous configuration.
  4. Tune label style via the controls bar.
  5. Build — galleries are saved to disk automatically next to each source folder.

All folders share the same layout. Each folder produces one gallery PNG.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from renderer import (
    count_labeled_cells,
    load_layout,
    render_gallery,
    render_preview,
    scan_images,
)

# ─── Session state keys ───────────────────────────────────────────────────────
_FOLDERS       = "mg_folders"        # list[str]
_LAYOUT        = "mg_layout"         # pd.DataFrame | None  — raw from file
_LAYOUT_EDITED = "mg_layout_edited"  # pd.DataFrame | None  — working/editable copy
_LAYOUT_SIG    = "mg_layout_sig"     # tuple — detects new layout upload
_LAYOUT_ED_V   = "mg_layout_ed_v"    # int   — version key to force data_editor reset
_RESULTS       = "mg_results"        # list[str] | None  — saved output paths
_PATH_INPUT    = "mg_path_input"     # str
_SETTINGS_SIG  = "mg_settings_sig"   # tuple — detects new settings upload
_SETTINGS_NAME = "mg_settings_name"  # str   — filename of loaded settings
_LAYOUT_NAME   = "mg_layout_name"    # str   — filename of loaded layout
_BUILD_ERRORS  = "mg_build_errors"   # list[str] — errors from last build

# Display settings
_FONT_SCALE    = "mg_font_scale"
_LABEL_H       = "mg_label_h"
_PADDING       = "mg_padding"
_LABEL_BG_ON   = "mg_label_bg_on"
_LABEL_BG      = "mg_label_bg"
_TEXT_COLOR    = "mg_text_color"
_ZOOM          = "mg_zoom"


# ─── State helpers ────────────────────────────────────────────────────────────

def _init_state() -> None:
    st.session_state.setdefault(_FOLDERS,       [])
    st.session_state.setdefault(_LAYOUT,        None)
    st.session_state.setdefault(_LAYOUT_EDITED, None)
    st.session_state.setdefault(_LAYOUT_SIG,    None)
    st.session_state.setdefault(_LAYOUT_ED_V,   0)
    st.session_state.setdefault(_RESULTS,       None)
    st.session_state.setdefault(_PATH_INPUT,    "")
    st.session_state.setdefault(_SETTINGS_SIG,  None)
    st.session_state.setdefault(_SETTINGS_NAME, "")
    st.session_state.setdefault(_LAYOUT_NAME,   "")
    st.session_state.setdefault(_BUILD_ERRORS,  [])
    st.session_state.setdefault(_FONT_SCALE,    8)
    st.session_state.setdefault(_LABEL_H,       36)
    st.session_state.setdefault(_PADDING,       6)
    st.session_state.setdefault(_LABEL_BG_ON,   False)
    st.session_state.setdefault(_LABEL_BG,      "#FFFFFF")
    st.session_state.setdefault(_TEXT_COLOR,    "#FFFFFF")
    st.session_state.setdefault(_ZOOM,          40)


def _browse_folder() -> str:
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes("-topmost", 1)
        path = filedialog.askdirectory(title="Select image folder")
        root.destroy()
        return path or ""
    except Exception:
        return ""


def _file_sig(file) -> tuple:
    return (file.name, len(file.getvalue()))


def _current_settings() -> dict:
    return {
        "font_scale":  st.session_state[_FONT_SCALE],
        "label_h":     st.session_state[_LABEL_H],
        "padding":     st.session_state[_PADDING],
        "label_bg_on": st.session_state[_LABEL_BG_ON],
        "label_bg":    st.session_state[_LABEL_BG],
        "text_color":  st.session_state[_TEXT_COLOR],
    }


# ─── Settings save / load ─────────────────────────────────────────────────────

def _settings_to_json() -> bytes:
    edited = st.session_state[_LAYOUT_EDITED]
    payload = {
        "version":     1,
        "font_scale":  int(st.session_state[_FONT_SCALE]),
        "label_h":     int(st.session_state[_LABEL_H]),
        "padding":     int(st.session_state[_PADDING]),
        "label_bg_on": bool(st.session_state[_LABEL_BG_ON]),
        "label_bg":    str(st.session_state[_LABEL_BG]),
        "text_color":  str(st.session_state[_TEXT_COLOR]),
        "zoom":        int(st.session_state[_ZOOM]),
        "layout_grid": edited.values.tolist() if edited is not None else None,
    }
    return json.dumps(payload, indent=2).encode()


def _apply_settings(payload: dict) -> None:
    for src, dst in (
        ("font_scale",  _FONT_SCALE),
        ("label_h",     _LABEL_H),
        ("padding",     _PADDING),
        ("label_bg_on", _LABEL_BG_ON),
        ("label_bg",    _LABEL_BG),
        ("text_color",  _TEXT_COLOR),
        ("zoom",        _ZOOM),
    ):
        if src in payload:
            st.session_state[dst] = payload[src]

    grid = payload.get("layout_grid")
    if isinstance(grid, list) and grid:
        df = pd.DataFrame(grid).fillna("").astype(str)
        st.session_state[_LAYOUT_EDITED] = df
        st.session_state[_LAYOUT_ED_V]  += 1


# ─── CSS ──────────────────────────────────────────────────────────────────────

_CSS = """
<style>
/* Strip the outer box/border from every file uploader widget */
[data-testid="stFileUploader"] > div {
    border: none !important;
    padding: 0 !important;
    background: transparent !important;
    box-shadow: none !important;
}
/* Keep the drop-zone itself compact but visible */
[data-testid="stFileUploaderDropzoneInstructions"] {display: none;}
[data-testid="stFileUploaderDropzone"] small        {display: none;}
[data-testid="stFileUploaderDropzone"] svg          {display: none;}
[data-testid="stFileUploaderDropzone"] {
    min-height: 2.4rem;
    padding: 0.15rem 0.6rem;
    border-radius: 8px;
}
/* Centered number inputs */
[data-testid="stNumberInput"] input {text-align: center;}
/* Cap color picker width so it doesn't balloon on wide screens */
div[data-testid="stColorPicker"] {max-width: 130px;}
/* Hide Streamlit's built-in uploaded-file chip — we render our own display below */
[data-testid="stFileUploaderFile"]  { display: none !important; }
[data-testid="stFileUploader"] ul   { display: none !important; }
/* Subtle group labels above control clusters */
.mg-group {
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: #aaa;
    margin-bottom: 0.1rem;
}
</style>
"""


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(page_title="MicroGallery", layout="wide")
    st.markdown(_CSS, unsafe_allow_html=True)
    _init_state()

    st.title("MicroGallery")

    # ── Row 1: Image folders | Layout file | Settings ─────────────────────────
    folders_col, layout_col, settings_col = st.columns([1.8, 1, 1], gap="large")

    with folders_col:
        st.markdown("<div class='mg-group'>Image Folders</div>", unsafe_allow_html=True)
        path_c, browse_c, add_c = st.columns([3.6, 0.7, 0.6], gap="small")
        with path_c:
            typed = st.text_input(
                "path",
                value=st.session_state[_PATH_INPUT],
                label_visibility="collapsed",
                placeholder="Paste a folder path and click Add, or use Browse →",
            )
            st.session_state[_PATH_INPUT] = typed
        with browse_c:
            if st.button("Browse", use_container_width=True):
                picked = _browse_folder()
                if picked:
                    folder = str(Path(picked))
                    if folder not in st.session_state[_FOLDERS]:
                        st.session_state[_FOLDERS].append(folder)
                        st.session_state[_RESULTS] = None
                    st.rerun()
        with add_c:
            if st.button("Add", use_container_width=True, type="primary"):
                raw = st.session_state.get(_PATH_INPUT, "").strip()
                folder = str(Path(raw)) if raw else ""
                if not folder:
                    st.warning("Enter a folder path first.")
                elif not Path(folder).is_dir():
                    st.error(f"Not a valid directory: {folder}")
                elif folder in st.session_state[_FOLDERS]:
                    st.info("Folder already in list.")
                else:
                    st.session_state[_FOLDERS].append(folder)
                    st.session_state[_PATH_INPUT] = ""
                    st.session_state[_RESULTS] = None
                    st.rerun()

        for i, folder in enumerate(st.session_state[_FOLDERS]):
            item_c, rm_c = st.columns([9, 0.6], gap="small")
            with item_c:
                st.caption(f"📁  **{Path(folder).name}** — `{folder}`")
            with rm_c:
                if st.button("✕", key=f"rm_{i}", help="Remove"):
                    st.session_state[_FOLDERS].pop(i)
                    st.session_state[_RESULTS] = None
                    st.rerun()

    with layout_col:
        st.markdown("<div class='mg-group'>Layout File</div>", unsafe_allow_html=True)
        layout_file = st.file_uploader(
            "layout",
            type=["csv", "xls", "xlsx"],
            label_visibility="collapsed",
            help=(
                "CSV or Excel grid. Filled cells → labeled image slots "
                "(images assigned alphabetically, left-to-right, top-to-bottom). "
                "Empty cells → blank slots."
            ),
        )
        if layout_file:
            sig = _file_sig(layout_file)
            if st.session_state[_LAYOUT_SIG] != sig:
                try:
                    df = load_layout(layout_file)
                    st.session_state[_LAYOUT]        = df
                    st.session_state[_LAYOUT_EDITED] = df.copy()
                    st.session_state[_LAYOUT_SIG]    = sig
                    st.session_state[_LAYOUT_ED_V]  += 1
                    st.session_state[_LAYOUT_NAME]   = layout_file.name
                    st.session_state[_RESULTS]       = None
                except Exception as exc:
                    st.error(f"Layout parse error: {exc}")

        edited = st.session_state[_LAYOUT_EDITED]
        if edited is not None:
            item_c, rm_c = st.columns([9, 0.6], gap="small")
            with item_c:
                st.caption(
                    f"📋  **{st.session_state[_LAYOUT_NAME]}**  —  "
                    f"{edited.shape[1]} × {edited.shape[0]}  •  "
                    f"{count_labeled_cells(edited)} labeled cells"
                )
            with rm_c:
                if st.button("✕", key="rm_layout", help="Clear layout"):
                    st.session_state[_LAYOUT]        = None
                    st.session_state[_LAYOUT_EDITED] = None
                    st.session_state[_LAYOUT_NAME]   = ""
                    st.session_state[_LAYOUT_SIG]    = None
                    st.session_state[_RESULTS]       = None
                    st.rerun()

    with settings_col:
        st.markdown("<div class='mg-group'>Settings</div>", unsafe_allow_html=True)
        settings_file = st.file_uploader(
            "settings",
            type=["json"],
            label_visibility="collapsed",
            help="Restore label style, display settings, and layout labels from a previous session.",
        )
        if settings_file:
            sig = _file_sig(settings_file)
            if st.session_state[_SETTINGS_SIG] != sig:
                try:
                    _apply_settings(json.loads(settings_file.getvalue().decode()))
                    st.session_state[_SETTINGS_SIG]  = sig
                    st.session_state[_SETTINGS_NAME] = settings_file.name
                    st.session_state[_RESULTS]       = None
                    st.rerun()
                except Exception as exc:
                    st.error(f"Settings error: {exc}")

        if st.session_state[_SETTINGS_NAME]:
            item_c, rm_c = st.columns([9, 0.6], gap="small")
            with item_c:
                st.caption(f"⚙️  **{st.session_state[_SETTINGS_NAME]}**")
            with rm_c:
                if st.button("✕", key="rm_settings", help="Clear settings"):
                    st.session_state[_SETTINGS_SIG]  = None
                    st.session_state[_SETTINGS_NAME] = ""
                    st.rerun()

        if st.session_state[_LAYOUT_EDITED] is not None:
            st.download_button(
                label="Save Settings",
                data=_settings_to_json(),
                file_name="microgallery_settings.json",
                mime="application/json",
                use_container_width=True,
            )

    # ── Guard: controls and preview only render when ready ────────────────────
    ready = len(st.session_state[_FOLDERS]) > 0 and st.session_state[_LAYOUT_EDITED] is not None
    if not ready:
        st.info(
            "Add at least one image folder to continue."
            if not st.session_state[_FOLDERS]
            else "Upload a layout file to continue."
        )
        return

    edited_layout: pd.DataFrame = st.session_state[_LAYOUT_EDITED]
    folders: list[str] = st.session_state[_FOLDERS]
    n_folders = len(folders)

    # ── Controls (3 groups) ───────────────────────────────────────────────────
    st.divider()
    label_grp, color_grp, display_grp = st.columns([3, 2, 1], gap="large")

    with label_grp:
        st.markdown("<div class='mg-group'>Label Style</div>", unsafe_allow_html=True)
        lc1, lc2, lc3 = st.columns(3, gap="small")
        with lc1:
            st.session_state[_FONT_SCALE] = int(st.session_state[_FONT_SCALE])
            st.number_input("Font %",       min_value=1,  max_value=30,  step=1, key=_FONT_SCALE)
        with lc2:
            st.session_state[_LABEL_H] = int(st.session_state[_LABEL_H])
            st.number_input("Label height", min_value=0,  max_value=120, step=2, key=_LABEL_H)
        with lc3:
            st.session_state[_PADDING] = int(st.session_state[_PADDING])
            st.number_input("Padding",      min_value=0,  max_value=48,  step=1, key=_PADDING)

    with color_grp:
        st.markdown("<div class='mg-group'>Colors</div>", unsafe_allow_html=True)
        cc1, cc2, cc3 = st.columns([0.7, 1, 1], gap="small")
        with cc1:
            # Spacer aligns checkbox with the color picker swatches below their labels
            st.markdown("<div style='height:1.4rem'></div>", unsafe_allow_html=True)
            st.checkbox("Label BG", key=_LABEL_BG_ON)
        with cc2:
            st.color_picker("BG color",   key=_LABEL_BG,   disabled=not st.session_state[_LABEL_BG_ON])
        with cc3:
            st.color_picker("Text color", key=_TEXT_COLOR)

    with display_grp:
        st.markdown("<div class='mg-group'>Display</div>", unsafe_allow_html=True)
        st.session_state[_ZOOM] = int(st.session_state[_ZOOM])
        st.number_input("Preview %", min_value=10, max_value=200, step=5, key=_ZOOM)

    # ── Build button — full width below controls ───────────────────────────────
    build_label = "Build Gallery" if n_folders <= 1 else f"Build {n_folders} Galleries"
    if st.button(build_label, type="primary", use_container_width=True):
        layout_snap   = st.session_state[_LAYOUT_EDITED]
        settings_snap = _current_settings()
        saved:  list[str] = []
        errors: list[str] = []
        bar = st.progress(0, text="Building…")
        for idx, folder in enumerate(folders):
            bar.progress(idx / n_folders, text=f"Rendering {Path(folder).name}…")
            try:
                img = render_gallery(folder, layout_snap, settings_snap)
                out = Path(folder).parent / (Path(folder).name + "_gallery.png")
                img.save(str(out), format="PNG", optimize=False, compress_level=1)
                saved.append(str(out))
            except Exception as exc:
                errors.append(f"{Path(folder).name}: {exc}")
        bar.empty()
        st.session_state[_RESULTS]      = saved
        st.session_state[_BUILD_ERRORS] = errors
        st.rerun()

    # Build results (rendered below button on rerun after build)
    if st.session_state[_RESULTS] is not None:
        for e in st.session_state[_BUILD_ERRORS]:
            st.error(e)
        for path in st.session_state[_RESULTS]:
            st.success(f"Saved → {path}")

    st.divider()

    # ── Layout editor + Preview ───────────────────────────────────────────────
    # Define effective_layout before columns so preview_col can read it after
    # editor_col sets it.
    effective_layout = edited_layout

    editor_col, preview_col = st.columns([1.5, 1], gap="large")

    with editor_col:
        st.subheader("Layout")
        col_config = {
            col: st.column_config.TextColumn(str(i + 1), width="small")
            for i, col in enumerate(edited_layout.columns)
        }
        effective_layout = st.data_editor(
            edited_layout,
            use_container_width=True,
            num_rows="fixed",
            hide_index=True,
            column_config=col_config,
            height=min(620, 36 * edited_layout.shape[0] + 38),
            key=f"layout_editor_{st.session_state[_LAYOUT_ED_V]}",
        )
        if not effective_layout.equals(edited_layout):
            st.session_state[_LAYOUT_EDITED] = effective_layout
            st.session_state[_RESULTS] = None

        for folder in folders:
            imgs = scan_images(folder)
            n_cells = count_labeled_cells(effective_layout)
            delta = len(imgs) - n_cells
            note = (
                f"  ⚠️ {delta} image(s) ignored" if delta > 0
                else f"  ⚠️ {-delta} cell(s) will be empty" if delta < 0
                else "  ✓ images match cells"
            )
            st.caption(f"📁 **{Path(folder).name}**: {len(imgs)} images · {n_cells} cells{note}")

    with preview_col:
        st.subheader("Preview")
        try:
            tile, cell_w, cell_h = render_preview(folders[0], effective_layout, _current_settings())
            zoom = st.session_state[_ZOOM]
            st.image(tile, width=max(80, int(tile.width * zoom / 100)))
            st.caption(f"First folder · first tile · cell {cell_w} × {cell_h} px · zoom {zoom}%")
        except Exception as exc:
            st.warning(f"Preview unavailable: {exc}")


if __name__ == "__main__":
    main()
