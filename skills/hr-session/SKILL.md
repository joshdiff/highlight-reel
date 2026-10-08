---
name: hr-session
description: Plan a day of highlight work — point at the day's game folders or card dumps; detects cameras and footage shapes, matches teams/players/clients from the library (pick existing players or add new ones), takes the deliverable orders, and writes the session queue that /highlight-reel runs. The only stage that asks questions.
---

# hr-session — plan the day (the ONLY place questions are asked)

$ARGUMENTS

`S=$(dirname "$(find -L ~/.claude/skills ~/.claude/plugins -name hrstate.py -path '*highlight-reel/scripts/*' 2>/dev/null | head -1)")`. Library tools: `hrprofile.py` (players/teams), `library.py` (clients/brands), `cameras.py` (cameras), `sports.py` (packs).

Ask with `AskUserQuestion` in as few rounds as possible: up to 4 questions per round, recommended option first ("Other" is automatic). Pre-fill everything you can from `$ARGUMENTS`, folder names and the library, and ask only what's missing.

## 1. Find the footage
- `hrstate.py config` gives media_root. With no folders given, list recent game folders: `ls -td "<media_root>"/*/*/*/ | head -12`, plus any folder modified today (card dumps).
- Ask which folders are today's games (multiSelect, newest first). One game can span several folders (two cameras or cards); group folders by game when names or dates match, and confirm.

## 2. Per game: cameras, footage shape, sport, teams
1. `python3 $S/cameras.py probe <folder…>` (metadata only, ~1s/100 files). It reports:
   - clips per known camera;
   - UNKNOWN groups, with suggested presets;
   - mixed fps, VFR, portrait clips;
   - files long enough to need segmentation (long continuous recordings).
2. For each UNKNOWN group, ask "What shot the `<prefix>` clips (<codec> <WxH> <fps>)?". Options: suggested presets first, existing camera profiles, "Already-edited export — skip", Other. Follow up for the picture profile (Log/HDR/standard) when the preset doesn't settle it. Create it with `cameras.py new <id> --from-preset <p> --prefix … [--encoding …]` and re-probe until nothing is UNKNOWN. For an AI camera with exported event tags, ask for the tag file (used in /hr-ingest).
3. **Sport** (`python3 $S/sports.py list`): guess from the team profile or folder name, and confirm.
4. **Teams:** home and away. Offer library teams (`hrprofile.py list teams`), matched by media folder / name, plus "New team". Ask which kit each wore when the profile has more than one. A team with no reels ordered still needs a name (the opponent).
5. **Date and event:** from the folder name ("3-22-26 vs Rovers" → 2026-03-22, "Rovers") or the clips' creation time.

## 3. Orders: who gets what
- **Clients** (`library.py list clients`): which client(s) these games are for. A client's `default_orders` pre-fill the orders, e.g. "team scoring reel + social reel per rostered player".
- **Players:** offer existing players **most recent first**: `hrprofile.py list players --recent`, shown as "Name #N (Team) — N games, last <date>". Filter to the game's teams first, then the client's players. Always include **"Add new player"**, which runs the `/hr-library` add-player flow inline (name, team, number, grad year, look). A new player's look can be thin; it gets learned in hr-find.
- **Per order:** target (player or team), type (social_reel, recruiting_tape, scoring_reel, season_reel), aspects (9:16 / 1:1 / 4:5 / 16:9; default from type), finish path (ffmpeg default; Resolve if they want to grade in Resolve), brand (the client's), priority (what they need first).
- **Season reel for a player:** it uses their profile's game history. Mention how many games it would draw from (`hrprofile.py brief <id>` → games processed).

## 4. Confirm and write
Show one screen:
- games, with clip count per camera, long files and sport;
- teams;
- orders, with client, aspects, path and priority;
- estimated work (survey ≈ 3–5 min per 100 clips; segmentation ≈ 1 min per 10 min of long footage);
- where files will go (`naming.py` templates).

Ask once: "Start the session?" (Start / Change something). Then write:
```
hrstate.py new-session "<YYYY-MM-DD>[ <name>]"
# per game
hrstate.py new-game --date D --home "Home" --away "Away" --sport S --source DIR [--source DIR2] \
      --home-team <team_id> [--away-team <team_id>] [--home-kit home] [--away-kit away]
hrstate.py session add-game
# per order (targets are shared: one player in one game = one target, however many reels)
hrstate.py new-target <player_id or team slug> --kind player|team [--player <player_id>] --team <team_id|home|away>
hrstate.py new-deliv <id> --target <target> --type T --aspects 9:16,1:1 --finish ffmpeg|resolve --client C --brand B
hrstate.py session add-deliv "<game id>" <id> <priority>
```
Deliverable ids: `<who>-<type>`, e.g. `alex-social`, `riverside-scoring`. For a season reel, put it on the player's most recent game.

When invoked from /highlight-reel, continue straight into the queue (`hrstate.py next`) without asking anything else.
