---
name: hr-project
description: Highlight reel deliverable stage (Resolve path) — open or create the game's DaVinci Resolve project (colour management, 29.97, bins; one project per game, shared by its deliverables), set per-clip input colour spaces for mixed cameras, and import this deliverable's clips and reframes.
---

# hr-project — Resolve project, colour science, import

$ARGUMENTS

`S=$(dirname "$(find -L ~/.claude/skills ~/.claude/plugins -name hrstate.py -path '*highlight-reel/scripts/*' 2>/dev/null | head -1)")`. Shared rules: `$S/../reference/quality-bar.md`. Uses the davinci-resolve MCP; load the tool schemas with ToolSearch first.

**Scope: deliverable** (Resolve path: `finish_path` = resolve). Requires `direct` done. The project itself is GAME-level (`hrstate.py get resolve.project`); the second deliverable of a game reuses it.

## Steps
1. **Project.** If `hrstate.py get resolve.project` is set and that project exists (`project_manager` → `list`), open it and skip to step 4. Otherwise create "<game id>". If that name exists from an older run, create "<game id> v2" (v3…) instead of reusing it: old timelines can lock the frame rate, and old grades/node states leak in. Never delete the old project. Save the name with `hrstate.py set resolve.project "<name>"`.
2. **Settings** (`project_settings` → `set_setting`, then READ BACK each; sets can fail silently):
   - `colorScienceMode` = `davinciYRGBColorManagedv2`
   - `colorSpaceInput` = the Resolve name (`python3 $S/cameras.py encodings`) of the game's MOST COMMON encoding (`hrstate.py get media.encodings`). Use short names only; the long "X / Y" forms are rejected. Names flagged "verify" may need a different spelling: read back, try the variants Resolve lists, and fix `ENCODINGS` in cameras.py.
   - `colorSpaceTimeline` = `DaVinci WG/Intermediate`; `colorSpaceOutput` = `Rec.709 Gamma 2.4`
   - `timelineFrameRate` = `29.97` and `timelinePlaybackFrameRate` = `29.97`. Set these NOW, before any timeline exists; Resolve can lock the project rate once a timeline is created.
3. **Bins** (`media_pool` → `add_subfolder`, parent_path `Master/...`): `_SEQUENCES`, `FOOTAGE/originals`, `FOOTAGE/reframed`, `GRAPHICS`, `MUSIC`, `BRAND`.
4. **Import this deliverable's media:**
   - `Master/FOOTAGE/originals` ← the source files of the clips in `deliv get select` (paths from `media.clips`); skip any already imported (`resolve.media_ids`);
   - `Master/FOOTAGE/reframed` ← every `deliv get direct.renders.*.out`.

   Then `media_pool` → `probe_media_pool` → a name→ID map.
5. **Per-clip input colour space (mixed cameras):** every imported clip whose encoding differs from the project input gets its own "Input Color Space" (`media_pool_item` → `set_clip_property`), from `media.clips.<clip>.encoding` → cameras.py ENCODINGS. Reframes keep their SOURCE clip's encoding: vcam preserves Log, and converts full→video range explicitly (luma 140→184 is the expected shift for full-range Canon HEVC). Set it on every reframe and read back.
6. **Write state:**
   - game level: `hrstate.py merge resolve file.json` with `{"project": "...", "media_ids": {"R7__1630": "...", "R7__1630_9x16_vc": "..."}, "settings_readback": {...}}`;
   - deliverable: `hrstate.py deliv done project "<project>"`.

## Done when
All five settings read back as set, and every needed clip and reframe is in `resolve.media_ids` with the right input colour space.
