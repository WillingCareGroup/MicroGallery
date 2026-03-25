# MicroGallery — Claude Standing Instructions

## Read at the start of every session
1. `HANDOFF.md` — current state, open questions, recommended next steps
2. `docs/invariants.md` — constraints that must never be violated
3. Last 10 entries of `docs/devlog.md` — recent decisions and context

---

## File map

| File | Role |
|------|------|
| `app.py` | Streamlit UI — session state, widgets, layout, user interaction |
| `renderer.py` | Pure image logic — no Streamlit imports, no side effects |
| `requirements.txt` | Python dependencies |
| `run.bat` | Windows double-click launcher (activates venv, runs Streamlit) |
| `docs/invariants.md` | Hard constraints on behaviour and architecture |
| `docs/devlog.md` | Running log of decisions, pitfalls, and trade-offs |
| `HANDOFF.md` | Session-to-session continuity document |

---

## Scope guard

Stop and write a plan before touching any code if the task requires:
- Creating more than 2 new files, **OR**
- Modifying more than 4 existing files, **OR**
- Changing any public function signature in `renderer.py`, **OR**
- Adding or removing entries in `requirements.txt`, **OR**
- Changing how images are assigned to layout cells

Exception: user has explicitly said "proceed autonomously" for this session.

---

## Requires explicit user approval
- Any change to the image-to-cell assignment logic (`renderer.assign_cells`)
- New entries in `requirements.txt`
- Changes to the layout file format or how it is parsed
- Removing any existing user-facing feature

## Claude decides autonomously
- Implementation details within a function
- Variable naming and code style
- Error message wording
- CSS tweaks and visual polish
- Comment and docstring content
- Streamlit widget layout within an already-agreed section

---

## Architecture reminders

**renderer.py is a pure library — keep it that way:**
- Zero Streamlit imports, ever
- All functions take plain Python types (str, dict, pd.DataFrame, Path)
- No global state, no side effects beyond returning values
- Adding a new render feature = add a function here, wire it in app.py

**app.py owns all state and UI:**
- Session state keys are defined as module-level constants (`_FOLDERS`, `_LAYOUT`, etc.)
- `_init_state()` sets all defaults with `setdefault` — add new keys here
- `_current_settings()` is the single place that assembles the settings dict for renderer calls

**Cell assignment is the core contract (see invariants.md):**
- Images sorted alphabetically by filename
- Assigned to non-empty layout cells in row-major order (left→right, top→bottom)
- This must match user expectations — any change needs explicit discussion

---

## Known Streamlit pitfalls — do not re-introduce

**`number_input` key= initialization bug:**
`st.number_input(key=X)` with `st.session_state.setdefault(X, N)` displays the correct
value but the internal widget value starts at `min_value`. The first arrow-click snaps to
`min_value + step`. Fix: always use `value=int(st.session_state[X])` without `key=`,
and sync back manually: `st.session_state[X] = returned_value`.

**Widget key cannot be set after render:**
`st.session_state[key] = value` raises `StreamlitAPIException` if the widget with that
key has already rendered in the current run. Fix: use `value=` parameter instead of
`key=` for any widget whose value needs to be set programmatically (e.g. the path
text_input populated by the Browse dialog).

**Button clicks and st.rerun():**
Setting session state and calling `st.rerun()` in a button handler is the correct
pattern for actions that change app structure (adding a folder, clearing results).
Do not try to update dependent widgets in the same run — rerun and let them re-render.

---

## Dev log protocol

When making a significant decision (architecture, trade-off, tech debt accepted,
approach rejected, pitfall discovered), append an entry to `docs/devlog.md`:

```
### YYYY-MM-DD — <short title>
**Type:** Decision | ADR | Pitfall | Fix | Discovery
**Context:** what situation led to this
**Decision:** what was decided
**Why:** driving reason
**Alternatives considered:** what was rejected and why
**Trade-offs / tech debt:** what this sacrifices or defers
**Pitfalls to watch:** known risks or future gotchas
```

Mark uncertain facts with `[ASSUMED]` and verified facts with `[VERIFIED]`.

---

## End of session

Update `HANDOFF.md` with:
- What was completed this session
- Current working state (what works, what doesn't, any known bugs)
- Open questions or unresolved decisions
- Recommended next steps in priority order
