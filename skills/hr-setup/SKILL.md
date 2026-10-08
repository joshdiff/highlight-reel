---
name: hr-setup
description: Highlight reel stage 1 — guided setup (pick-lists for player/team, game folder, deliverable, camera, grade) that creates the per-game workspace and reel.json. Arguments optional (free text like "social reel for #7 from Saturday's game").
---

# hr-setup — guided setup (the ONLY stage that asks the user anything)

$ARGUMENTS

`S=$(dirname "$(find -L ~/.claude/skills ~/.claude/plugins -name hrstate.py -path '*highlight-reel/scripts/*' 2>/dev/null | head -1)")` (the scripts folder, wherever the skill is installed). Shared rules: `$S/../reference/quality-bar.md`.

## Settings to fill (→ `settings.*` in reel.json)
- `reel_mode`: `player` | `team`
- `player_number`, `player_name`, `grad_year` (player mode; grad_year optional → lower third "[team_name] - c/o [grad_year]")
- `team_name`, `team_jersey_color`
- `source_folder`, `event_name` (opponent / event, e.g. "Rovers")
- `deliverable_type`: social_reel | recruiting_tape | goals_reel
- `camera_profile`: canon_clog3 | sony_slog3 | rec709
- `power_grade_drx` (path), `output_folder`
- `output_name`: `[team_name]_[player_number or "Team"]_[deliverable_type]_[event_name].mp4`

## Steps
1. Pre-fill from `$ARGUMENTS`: free text ("social reel for #7 from Saturday's game") or the old pipe order (player_number | player_name | team_name | team_jersey_color | event_name | source_folder | deliverable_type | camera_profile | power_grade_drx | output_folder | grad_year — `team`/`all`/`-` as player_number = team mode). Only ask for what's still missing.
2. Read memory first so pick-lists offer known players/teams (name, number, team, jersey colour, grad year). Read machine defaults with `python3 $S/hrstate.py config` (media_root, output_folder, power_grade_drx, camera_profile). **First run on a machine** (config empty): ask for these in Round 3 and save each with `hrstate.py config KEY VALUE`. Camera default when unknown: canon_clog3.
3. Find game folders before asking: `ls -td "<media_root>"/*/"<team>"/*/ | head`. Offer the 3 newest; derive event_name from the folder name ("3-22-26 vs Rovers" → "Rovers", "VS United" → "United") and show it in the option label. Count the video files in the chosen folder (`find -L DIR -maxdepth 1 -iname '*.mp4' -o -iname '*.mov' | wc -l`). Also run `python3 $S/hrstate.py list` — if a workspace for this game already exists, offer "Resume existing (stages done: …)" vs "Start fresh".
4. Ask with `AskUserQuestion`, as few rounds as possible (max 4 questions/round, recommended option first; "Other" is automatic):
   - Round 1: Reel type (Player highlight / Full team) · Deliverable (Social reel 9:16 / Recruiting tape / Goals reel) · Team (known teams + Other)
   - Round 2: Player (player mode: known players as "Name #N" + Other) · Game folder (3 newest, labelled with event) · Camera (Canon Log 3 / Sony S-Log3 / Rec.709)
   - Round 3 (only if not known from memory/config): jersey colour, grad year, and on first run media root, grade file, output folder
   For a player or team not in memory, take the "Other" text and ask follow-ups (number, jersey colour) next round.
5. Show a one-screen summary of every setting (with the clip count and output filename) and ask once: "Start the reel?" (Start / Change something). On "Change something", ask only for the item(s) to change.
6. Write the state:
   ```
   python3 $S/hrstate.py init --team "<team_name>" --event "<event_name>" --output "<output_folder>" --source "<source_folder>"
   python3 $S/hrstate.py merge settings /path/to/settings.json      # every setting above
   python3 $S/hrstate.py done setup "<one-line summary>"
   ```
   "Start fresh" on an existing workspace: `hrstate.py reset survey` after init (keeps the folder, clears later stages).

## Done when
`hrstate.py status` shows every setting filled (grad_year may be empty) and `setup` done. When invoked by /highlight-reel, continue to hr-survey without asking anything else.

## Known gaps
- Jersey colour is free text; hr-survey calibrates the actual HSV range. Could offer a frame picker here instead.
