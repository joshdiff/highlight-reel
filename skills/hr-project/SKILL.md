---
name: hr-project
description: Highlight reel stage 6 — create the DaVinci Resolve project with colour management for the camera, 29.97 timeline rate, bins, and import the original clips and the vcam reframes.
---

# hr-project — Resolve project, colour science, bins, import

$ARGUMENTS

`S=$(dirname "$(find -L ~/.claude/skills ~/.claude/plugins -name hrstate.py -path '*highlight-reel/scripts/*' 2>/dev/null | head -1)")` (the scripts folder, wherever the skill is installed). Shared rules: `$S/../reference/quality-bar.md`. Uses the davinci-resolve MCP (load tool schemas with ToolSearch first).

**Workspace:** if `$ARGUMENTS` names a game, `hrstate.py use "<game>"`; then `hrstate.py status`. Requires `direct` done (social_reel) or `select` done (16:9 deliverables).

## Steps
1. `project_manager` → `list`. If "[team_name] - [event_name]" does not exist, create it. If it exists (a previous run), create "[team_name] - [event_name] v2" (v3…) instead of reusing it — old timelines can lock the frame rate and old grades/node states leak in. Never delete the old project.
2. `project_settings` → `set_setting`, then READ BACK each (sets can fail silently):
   - `colorScienceMode` = `davinciYRGBColorManagedv2`
   - `colorSpaceInput` = the Resolve name (`python3 $S/cameras.py encodings`) of the game's MOST COMMON encoding (`hrstate.py get media.encodings`). Short names only; the long "X / Y" forms are rejected. Names flagged "verify" may need a different spelling — read back, and if rejected, try the variants Resolve lists and fix `ENCODINGS` in cameras.py.
   - `colorSpaceTimeline` = `DaVinci WG/Intermediate`
   - `colorSpaceOutput` = `Rec.709 Gamma 2.4`
   - `timelineFrameRate` = `29.97` and `timelinePlaybackFrameRate` = `29.97` — set NOW, before any timeline exists; Resolve can lock the project rate once a timeline is created.
3. Bins with `media_pool` → `add_subfolder` (parent_path `Master/...`): `_SEQUENCES/{Social_Reel,Recruiting,Goals_Reel}`, `FOOTAGE/[event_name]`, `FOOTAGE/[event_name]_reframed`, `SELECTS/{Goals,Skills,Player_[player_number]}`, `GRAPHICS`, `MUSIC`.
4. Import: `set_current_folder` `Master/FOOTAGE/[event_name]`; `media_storage` → `import_to_pool` with only the clips used in `select` (paths from `media.clips`). Then `Master/FOOTAGE/[event_name]_reframed` ← every `direct.renders.*.out`.
5. `media_pool` → `probe_media_pool` → name→ID map.
6. **Per-clip input colour space (mixed cameras):** every imported clip whose encoding differs from the project input gets its own "Input Color Space" (`media_pool_item` → `set_clip_property`) from `media.clips.<clip>.encoding` → cameras.py ENCODINGS. Reframes (`<clip>_vc`) keep their SOURCE clip's encoding — vcam preserves Log (it converts full→video range explicitly; luma 140→184 is the expected shift for full-range Canon HEVC). Set it on every reframe and read back.
7. Write results: `hrstate.py merge resolve file.json` with `{"project": "...", "media_ids": {"R7__1630": "...", "R7__1630_vc": "..."}, "settings_readback": {...}}`. Then `hrstate.py done project "<project name>"`.

## Done when
All five settings read back as set; every needed clip and reframe is in `resolve.media_ids`.

## Known gaps
- Import of the whole folder isn't needed for the reel, but the selects timeline (hr-assemble) only covers chosen clips — revisit if the user wants all footage in the project.
