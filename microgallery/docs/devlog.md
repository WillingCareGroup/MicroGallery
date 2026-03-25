# MicroGallery — Dev Log

---

### 2026-03-24 — Settings/layout filename display + controls 3-row restructure
**Type:** Decision
**Context:** User requested two UI improvements: (1) settings column should display loaded filename with ✕ button in the same style as the image folder list, (2) controls bar: move Label BG toggle to the header sub-row alongside "COLORS" label, and move Build Gallery button to a dedicated full-width row below the controls.
**Decision:** Four coordinated changes:
1. Added `_SETTINGS_NAME`, `_LAYOUT_NAME`, `_BUILD_ERRORS` session state keys.
2. Layout column: stores `_LAYOUT_NAME = layout_file.name` on load; displays caption with filename + dimensions + ✕ button (same `item_c / rm_c` column pattern as folder list). ✕ button clears all layout state.
3. Settings column: stores `_SETTINGS_NAME = settings_file.name` on load; displays caption with filename + ✕ button when loaded. ✕ clears sig + name and reruns.
4. Controls restructured from 4-column single row to: 3-group columns (`[3, 2, 1]`) each with their own header+controls internally, Label BG toggle moved into the "Colors" header row (alongside the "COLORS" label using sub-columns `[1, 1.4]`), Build button moved to full-width row below the group columns, build results (errors + success paths) displayed from session state below the button on the next rerun (`_BUILD_ERRORS` + `_RESULTS is not None` gate).
**Why:** Consistent item display style across all three input columns; cleaner 3-row visual hierarchy for controls (header + controls + action).
**Alternatives considered:** Flat 6-column approach for all rows — rejected, harder to maintain and group labels wouldn't align cleanly with their controls.
**Trade-offs / tech debt:** Build results now persist until the next build or until folders/layout change (which sets `_RESULTS = None`, hiding results via the `is not None` gate).
**Pitfalls to watch:** `_BUILD_ERRORS` is not cleared when folders or layout change — it's hidden because `_RESULTS` becomes `None`, but the old list stays in session state. Not a problem currently but worth noting.

---

### 2026-03-24 — Layout editor, settings save/load, controls redesign, Build moved to top
**Type:** Decision
**Context:** Multiple UX improvements requested after initial working build.
**Decision:** Five changes in one pass:
1. `st.dataframe` → `st.data_editor` for layout (editable in-browser). Uses `_LAYOUT_EDITED` as the working copy separate from `_LAYOUT` (raw file). `_LAYOUT_ED_V` version key forces data_editor to reinitialize when a new file is uploaded or settings are loaded.
2. Removed outer box from file uploader via CSS (`[data-testid="stFileUploader"] > div { border: none }`).
3. Settings save/load: JSON file containing all UI settings + current layout grid. Load via uploader in a new Settings column. Save via download button. `_apply_settings()` restores all keys and bumps `_LAYOUT_ED_V` if grid is present.
4. Controls bar split into three labelled groups (Label Style | Colors | Display) using nested columns instead of one wide sparse row.
5. Build & Download row moved to Row 2 (below inputs), before the guard check. Build button disabled when inputs not ready.
**Why:** All five changes improve daily usability without architectural changes.
**Alternatives considered:** Settings in a sidebar — rejected, user wants everything visible on wide screen.
**Trade-offs / tech debt:** `effective_layout` variable is defined before the editor_col block and reassigned inside it, then read in preview_col. Works because Python `with` blocks don't create new scopes, but it's slightly implicit.
**Pitfalls to watch:** Any future `st.data_editor` must follow the `_LAYOUT_ED_V` pattern to force reset when data changes externally.

---

### 2026-03-24 — Initial build: web UI replacing CLI pipeline
**Type:** Decision
**Context:** User had a two-step CLI workflow: `getbe_v5.py` (scans folders → generates
`BE.xlsx` manifest) → `image_merger_v9.py` (reads BE.xlsx → renders grid PNGs). The existing
`app.py` / `core.py` Streamlit prototype had significant bugs and design issues.
**Decision:** Rewrote from scratch as `app.py` + `renderer.py` with no code reuse from the
old prototype.
**Why:** The old app.py had implicit asset-to-grid ordering (alphabetical sort assumption that
could silently break), ~15 session state keys with complex interdependencies, a reused
column variable (`color_a`) across two render phases, and no batch mode.
**Alternatives considered:** Patching the old app.py — rejected because the state management
bugs would require rewriting most of it anyway.
**Trade-offs / tech debt:** No in-browser label editing (the old app had an editable
`st.data_editor` grid). Layout is read-only from the uploaded file.
**Pitfalls to watch:** alphabetical sort is [ASSUMED] to match user's file-naming conventions.

---

### 2026-03-24 — Removed getbe step entirely
**Type:** Decision
**Context:** `getbe_v5.py` generated `BE.xlsx` as an intermediate manifest with fragile
character-slice path construction (`folder_name[2:6] + folder_name[7] + folder_name[9]`).
**Decision:** No manifest file. Input is folder path + layout Excel directly.
**Why:** Simpler workflow, fewer failure points, no assumption about folder naming convention.
**Alternatives considered:** Keeping BE.xlsx as optional input for backwards compatibility —
rejected to keep the interface clean.
**Trade-offs / tech debt:** Users with existing BE.xlsx workflows must adapt.
**Pitfalls to watch:** None.

---

### 2026-03-24 — number_input must use value= not key=
**Type:** Pitfall
**Context:** All control bar `number_input` widgets used `key=` with `st.session_state.setdefault`.
On first interaction the widget snapped to `min_value + step` (e.g. Preview % jumped from 40
to 15) because the internal widget value initialized to `min_value` regardless of session state.
**Decision:** All `number_input` widgets use `value=int(st.session_state[KEY])` without `key=`,
and sync back with `st.session_state[KEY] = returned_value`.
**Why:** Streamlit [VERIFIED] does not reliably propagate `setdefault` values to `number_input`
internal state on first load.
**Alternatives considered:** Using `st.session_state[key] = N` before widget render — does not
reliably fix it in all Streamlit versions.
**Trade-offs / tech debt:** Slightly more verbose widget code.
**Pitfalls to watch:** Any new `number_input` added to the controls bar must follow this pattern.

---

### 2026-03-24 — Browse button auto-adds folder without confirmation step
**Type:** Decision
**Context:** Original design had Browse → path fills text input → user clicks Add. User
reported this as an unnecessary extra step.
**Decision:** Browse dialog selection directly appends the folder to the batch list and reruns.
The text input + Add button remain for the manual-paste workflow.
**Why:** Browse is an explicit selection action; no confirmation needed.
**Alternatives considered:** Removing the text input entirely — rejected because manual
path paste is still useful for power users and remote paths.
**Trade-offs / tech debt:** None.
**Pitfalls to watch:** None.
