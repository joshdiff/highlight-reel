---
name: hr-project
description: Highlight reel deliverable stage (Resolve path) — open or create the game's DaVinci Resolve project (colour management, 29.97, bins; one project per game, shared by its deliverables). The footage itself comes in with the timeline in hr-assemble — the original files, never copies.
---

# hr-project — Resolve project and colour science

$ARGUMENTS

`S=$(dirname "$(find -L ~/.claude/skills ~/.claude/plugins -name hrstate.py -path '*highlight-reel/scripts/*' 2>/dev/null | head -1)")`. Shared rules: `$S/../reference/quality-bar.md`. Uses the davinci-resolve MCP; load the tool schemas with ToolSearch first.

**Scope: deliverable** (Resolve path: `finish_path` = resolve). Requires `direct` done. The project itself is GAME-level (`hrstate.py get resolve.project`); the second deliverable of a game reuses it.

The project only ever references the ORIGINAL source files. Nothing is rendered or copied for it: hr-assemble imports a timeline that trims the originals and carries the framing as Inspector keyframes, and Resolve imports the source clips with it.

## Steps
1. **Project.** If `hrstate.py get resolve.project` is set and that project exists (`project_manager` → `list`), open it and skip to step 4. Otherwise create "<game id>". If that name exists from an older run, create "<game id> v2" (v3…) instead of reusing it: old timelines can lock the frame rate, and old grades/node states leak in. Never delete the old project. Save the name with `hrstate.py set resolve.project "<name>"`.
2. **Settings** (`project_settings` → `set_setting`, then READ BACK each; sets can fail silently):
   - `colorScienceMode` = `davinciYRGBColorManagedv2`
   - `colorSpaceInput` = the Resolve name (`python3 $S/cameras.py encodings`) of the game's MOST COMMON encoding (`hrstate.py get media.encodings`). Use short names only; the long "X / Y" forms are rejected. Names flagged "verify" may need a different spelling: read back, try the variants Resolve lists, and fix `ENCODINGS` in cameras.py.
   - `colorSpaceTimeline` = `DaVinci WG/Intermediate`; `colorSpaceOutput` = `Rec.709 Gamma 2.4`
   - `timelineFrameRate` = `29.97` and `timelinePlaybackFrameRate` = `29.97`. Set these NOW, before any timeline exists; Resolve can lock the project rate once a timeline is created.
3. **Bins** (`media_pool` → `add_subfolder`, parent_path `Master/...`): `_SEQUENCES`, `GRAPHICS`, `MUSIC`, `BRAND`. (The timeline import puts the source clips in Master; hr-assemble moves them to `FOOTAGE`.)
4. **Write state:**
   - game level: `hrstate.py merge resolve file.json` with `{"project": "...", "settings_readback": {...}}`;
   - deliverable: `hrstate.py deliv done project "<project>"`.

## Done when
All five settings read back as set and the bins exist. (Clips and their input colour spaces are hr-assemble's job.)
