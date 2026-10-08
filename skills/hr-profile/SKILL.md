---
name: hr-profile
description: Highlight reel — build and edit the profiles reels are made from — players (name, team & number, look, decoys, lower third), teams (kits and calibrated jersey colours, roster, opponents) and cameras (how to recognise each camera's clips and its colour encoding). "list", "show <player>", "add player", "edit team", "add camera".
---

# hr-profile — players, teams, cameras

$ARGUMENTS

`S=$(dirname "$(find -L ~/.claude/skills ~/.claude/plugins -name hrstate.py -path '*highlight-reel/scripts/*' 2>/dev/null | head -1)")`

Profiles are local JSON (`~/.hr_work/players|teams|cameras/<id>.json`), never in the repo. Every reel reads them, and every reel writes back what it learned (hr-export), so identification gets better each game. Schemas with fictional examples: the repo's `examples/` folder. Tools: `python3 $S/hrprofile.py` (players/teams) and `python3 $S/cameras.py` (cameras) — run either with no args for help.

## What each profile holds
**Player** (`hrprofile.py new player ID --name "…" --team TEAM_ID --number N --grad YEAR`)
- `name`, `nickname`, `grad_year`, `lower_third` {line1, line2} (default line2 "[team] - c/o [grad]")
- `teams[]`: {team_id, number, position, seasons[], active} — a player can be on several teams (club, high school, ID camps) with different numbers; the game's team picks the number
- `appearance`: hair (colour, length, style — braid/ponytail/bun), build/height relative to teammates, boots (colour), accessories (headband, sleeves, captain band, knee brace), other
- `decoys[]`: things that fooled or could fool ID (teammate #17 vs #7, opponent wearing the same number)
- `notes[]` (dated lessons), `games[]` (date, event, team_id, best clips)

**Team** (`hrprofile.py new team ID --name "…" --folder "<media folder name>" --color "<shirt>"`)
- `media_folder` (the `<team>` folder name under media_root), `club`, `age_group`
- `kits`: {home|away|third: {shirt, shorts, socks, hsv: {<encoding>: {lo, hi}}}} — `hsv` is the calibrated OpenCV range per footage encoding, filled by hr-survey; don't hand-write it
- `roster` {number: who} (teammates worth knowing, e.g. number decoys), `opponents` {name: {shirt, notes}}

**Camera** (`cameras.py new ID --name "…" --type T --encoding E --prefix P [--brand B --codec C --make M --model M]`)
- `type`: mirrorless | cinema | phone | action | ai_panoramic | export (already-edited renders — skipped) | other
- `match`: how to recognise its files — every given field must match (filename prefix, container brand, codec, make/model tags). Get these from `cameras.py probe <folder>`.
- `encoding`: `cameras.py encodings` lists them (Canon Log 3, S-Log3, V-Log, Apple Log, HLG, PQ, Rec.709…). Metadata can't tell Log from standard — ask the user what picture profile they shoot.

## Steps
- **list / show:** `hrprofile.py list`, `hrprofile.py show player ID`, `hrprofile.py brief ID`, `cameras.py list`.
- **add player:** ask (AskUserQuestion, ≤2 rounds): name, team (existing teams + "new team"), number, grad year, then look — hair colour/length/style, anything distinctive (boots, sleeves, headband, captain band), position. Create with `new`, fill the rest with `set`/`merge`. Show `brief` at the end.
- **add team:** name, media folder (offer folders under `media_root/*/`), shirt/shorts/socks colours for home (and away if they have one).
- **add camera:** probe a folder with that camera's clips, show the signature, ask name/type/picture profile, create with `cameras.py new`, re-probe to confirm it matches.
- **edit:** `set player ID appearance.hair "…"`, `note player ID "…"`, etc. Confirm with `show`.
- Never write profile contents into the repo, the skill files, or anywhere outside `~/.hr_work`.
