---
name: hr-library
description: Highlight reel library — clients (output folders, naming, default orders), brands (colours, font, logo, lower third, watermark, intro/outro, music, loudness, grade), players (teams & numbers, look, reference photos, cue reliability, play style, game history, client feedback — they get smarter every game), teams (kits with calibrated shirt colours, roster, opponents) and cameras. "list", "show <player>", "add player", "add client", "brand assets", "feedback".
---

# hr-library — clients, brands, players, teams, cameras

$ARGUMENTS

`S=$(dirname "$(find -L ~/.claude/skills ~/.claude/plugins -name hrstate.py -path '*highlight-reel/scripts/*' 2>/dev/null | head -1)")`

Everything here is local (`~/.hr_work/library/`) and never goes in the repo; the repo's `examples/` folder has fictional samples of each kind. Tools, each printing help with no args:
- `hrprofile.py`: players and teams;
- `library.py`: clients and brands;
- `cameras.py`: cameras.

## How a player profile gets smarter
Every game that finds a player runs `hrprofile.py learn`. That saves:
- **Reference photos** (`refs/`, per kit): confirmed sightings that hr-find compares against next time (`hrprofile.py refsheet <id>`).
- **Cue reliability:** how often number / hair / footwear / build actually identified them, and what misled us. hr-find checks the most reliable cue first.
- **Dated look observations:** blanks get filled; changes (haircut, new number, new boots) are flagged for you to confirm.
- **Play style:** tallies of their events, foot/hand, positions and areas. Recruiting tapes lean on their strengths.
- **Game history:** best clips and delivered files per game. This is the source of season reels.
- **Client feedback:** keep/drop verdicts you record. Every future select obeys them.

`hrprofile.py brief <id>` shows all of it in one screen.

## Common tasks
- **List / show:**
  - `hrprofile.py list --recent` lists players by last game (this is the pick-list order in /hr-session);
  - `hrprofile.py brief <id>`, `hrprofile.py show player <id>`;
  - `library.py list`, `cameras.py list`.
- **Add a player:** ask (AskUserQuestion, ≤2 rounds) for name, team (existing teams + "new team"), number on that team, grad year (optional), sport, client, then the look: hair colour/length/style, footwear colour, accessories (headband, sleeves, captain band, knee brace), build/height relative to teammates. Then:
  ```
  hrprofile.py new player <id> --name "…" --team <team_id> --number N [--grad YEAR] [--sport S] [--client C]
  hrprofile.py set player <id> appearance.hair "…"        # etc.
  hrprofile.py set player <id> lower_third '{"line1": "…", "line2": "…"}'
  ```
  A player on several teams (club, school, camp) gets one entry per team: `merge player <id> teams …`, or let `learn` add it from a game.
  **Photos:** if the user has a clear photo of the player in kit, add it as a starting reference: `hrprofile.py ref add <id> --src <photo or video> --t 0 --box x0,y0,x1,y1 --kit home --cues hair,number`.
- **Add a team:** `hrprofile.py new team <id> --name "…" --sport S --folder "<media folder>" --color "<home shirt>" [--client C]`. Add an away kit with `set team <id> kits.away '{"shirt": "…"}'`. Shirt calibration (`kits.<kit>.hsv.<encoding>`) is filled by hr-survey; don't hand-write it.
- **Add a client:**
  ```
  library.py new client <id> --name "…" --brand <brand_id> [--output-root DIR] [--template "{team}/{date} {event}/{who}_{type}_{aspect}.mp4"]
  library.py order <id> --target player --type social_reel --aspects 9:16,1:1
  ```
  Template fields: `{client} {season} {team} {opponent} {date} {event} {sport} {who} {player} {number} {type} {aspect} {deliv}`.
- **Add a brand:**
  ```
  library.py new brand <id> --name "…" --primary "#RRGGBB" --secondary "#RRGGBB" --text "#FFFFFF"
  library.py asset <id> logo|watermark|intro|outro|font|music|creative_lut <file>
  library.py set brand <id> lower_third.position_y 0.8       # watermark.position br, loudness.social -14, …
  ```
  Ask about music licensing; record it with `library.py set brand <id> music.license_note "…"`.
- **Add a camera:** probe a folder of its clips (`cameras.py probe <dir>`), take the suggested preset or ask name/type/picture profile, then `cameras.py new <id> --from-preset <p> --prefix …`, and re-probe to confirm. If the user has the manufacturer's official Log→709 LUT: `cameras.py new … --lut <file.cube>`, or set `lut` on the profile.
- **Record client feedback** on a delivered reel: `hrprofile.py feedback <player> keep|drop "<what>" --deliv <id> [--clip C]`.
- **Fix a flag:** if a haircut or new number is confirmed, update `appearance` / `teams[].number` and clear the flag (`hrprofile.py set player <id> flags '[]'`).

Never copy profile contents into the repo, the skill files, or anywhere outside `~/.hr_work`.
