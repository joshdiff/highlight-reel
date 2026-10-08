---
name: hr-setup
description: Highlight reel stage 1 — guided setup for one game: pick the player profile (or full team), team and kit, game folder and deliverable; detects every camera in the folder; creates the game workspace and reel.json. Arguments optional (free text like "social reel for #7 from Saturday's game").
---

# hr-setup — this game (the ONLY stage that asks the user anything)

$ARGUMENTS

`S=$(dirname "$(find -L ~/.claude/skills ~/.claude/plugins -name hrstate.py -path '*highlight-reel/scripts/*' 2>/dev/null | head -1)")` (the scripts folder, wherever the skill is installed). Shared rules: `$S/../reference/quality-bar.md`.

Three layers — only the last is per game:
1. **Machine** (`hrstate.py config`): media_root, output_folder, power_grade_drx, ffmpeg. Set by `install.sh` / `/hr-config`.
2. **Profiles** (`hrprofile.py`, `cameras.py`): players, teams, cameras — built with `/hr-profile`, improved by every reel.
3. **This game** (`reel.json` `settings`): written here.

## Settings to fill (→ `settings.*`)
- `reel_mode`: `player` | `team`
- `player_id` (player mode) and `team_id` — profile ids; `kit` (home/away/third — which shirt our team wore)
- denormalised for convenience: `player_name`, `player_number` (from the player's membership in `team_id`), `team_name`, `team_jersey_color`, `grad_year`, `lower_third` [line1, line2]
- `source_folder`, `event_name` (opponent / event, e.g. "Rovers"), `game_date` if the folder name has one
- `deliverable_type`: social_reel | recruiting_tape | goals_reel
- `power_grade_drx` (default from config; per game override allowed), `output_folder` (from config)
- `output_name`: `[team_name]_[player_number or "Team"]_[deliverable_type]_[event_name].mp4`
- cameras are NOT a setting — they're detected per clip (step 4)

## Steps
1. **Machine check.** `python3 $S/hrstate.py config`. If media_root or output_folder is missing, run the `/hr-config` steps first (that's part of setup on a new machine).
2. **Pre-fill** from `$ARGUMENTS`: free text ("social reel for #7 from Saturday's game", a player name/nickname, a team, an opponent) or the legacy pipe order (player_number | player_name | team_name | team_jersey_color | event_name | source_folder | deliverable_type | camera | power_grade_drx | output_folder | grad_year). Match names against profiles. Only ask for what's still missing.
3. **Load profiles:** `python3 $S/hrprofile.py list`. Pick-lists offer players as "Name #N (Team)" and teams by name. For the chosen team, list game folders newest first: `ls -td "<media_root>"/*/"<team media_folder>"/*/ | head` — offer the 3 newest, labelled with the event derived from the folder name ("3-22-26 vs Rovers" → "Rovers", "VS United" → "United"). Also `hrstate.py list` — if a workspace for this game exists, offer "Resume (stages done: …)" vs "Start fresh".
4. **Cameras in this folder:** `python3 $S/cameras.py probe "<game folder>"` (metadata only, ~1s per 100 clips). It lists clips per known camera and groups UNKNOWN signatures. Report mixed frame rates (24/25 fps clips judder on a 29.97 timeline), VFR clips (phones) and portrait clips.
5. **Ask** with `AskUserQuestion`, as few rounds as possible (max 4 questions/round, recommended first; "Other" is automatic):
   - Round 1: Reel type (Player / Full team) · Deliverable (Social reel 9:16 / Recruiting tape / Goals reel) · Player (profiles as "Name #N (Team)" + "New player") or Team (team mode)
   - Round 2: Game folder (3 newest) · Kit worn (home/away — only if the team profile has more than one) · one question per UNKNOWN camera group: "What shot the `<prefix>` clips (<codec> <WxH> <fps>)?" with options from existing camera profiles + "Phone (standard/HDR)" + "Already-edited export — skip" + Other. Then a follow-up for the picture profile (Log type / HDR / standard) if it isn't implied.
   - New player / new team: run the `/hr-profile` add flow inline (name, team, number, grad year, look), then continue.
   Create camera profiles from the answers (`cameras.py new …`, match on the prefix + brand/codec from the probe) and re-probe until nothing is UNKNOWN.
6. **Summary + confirm:** one screen — player brief (`hrprofile.py brief <player_id> <team_id>`), team/kit, game folder with clip count per camera, deliverable, grade, output filename. Ask once: "Start the reel?" (Start / Change something). On "Change something", ask only for that item.
7. **Write state:**
   ```
   python3 $S/hrstate.py init --team "<team_name>" --event "<event_name>" --output "<output_folder>" --source "<source_folder>"
   python3 $S/hrstate.py merge settings /path/to/settings.json      # every setting above
   python3 $S/cameras.py assign                                     # per-clip camera/encoding into media.clips
   python3 $S/hrstate.py done setup "<one-line summary incl. cameras>"
   ```
   "Start fresh" on an existing workspace: `hrstate.py reset survey` after init.

## Done when
Every setting filled (grad_year may be empty), `cameras.py assign` reports no UNKNOWN cameras, `setup` done. When invoked by /highlight-reel, continue to hr-survey without asking anything else.
