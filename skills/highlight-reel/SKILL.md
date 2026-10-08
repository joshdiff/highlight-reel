---
name: highlight-reel
description: Sports highlight reels for any videographer — soccer, basketball, volleyball (sport packs), any camera mix, any number of clients, teams and players. Plan a day's footage with /hr-session, then this runs every game and deliverable autonomously (ingest → survey → find → select → direct → finish/Resolve → export), resumable. Also "status", "resume", "from <stage>", or a quick single reel.
---

# Highlight reel — run a session

$ARGUMENTS

`S=$(dirname "$(find -L ~/.claude/skills ~/.claude/plugins -name hrstate.py -path '*highlight-reel/scripts/*' 2>/dev/null | head -1)")` (this skill's `scripts/` folder). `python3 $S/hrstate.py` is the state tool; run it with no args for help.

## The model
```
Session (a day's footage)  →  Games (one survey each, shared)  →  Targets (a player or a team to find)
                                                              →  Deliverables (one reel each: type, aspects, brand, client)
```
- **Expensive work is done once per game:** ingest (cameras, long-file segmentation) and survey (frames, shirt calibration, detection).
- **Each target is found once:** hr-find, which also teaches the player's profile.
- **Each deliverable is cut, directed and finished separately**, through the **ffmpeg path** (`/hr-finish`, no NLE needed) or the **Resolve path** (`/hr-project` → `/hr-assemble` → `/hr-grade` → `/hr-title`). Both end with `/hr-export`.

| Scope | Stage | Command |
|---|---|---|
| — | plan the day | `/hr-session` (or `/hr-setup` for one quick reel) |
| game | ingest | `/hr-ingest` |
| game | survey | `/hr-survey` |
| target | find | `/hr-find` |
| deliverable | select → direct | `/hr-select`, `/hr-direct` |
| deliverable | finish (ffmpeg) | `/hr-finish` |
| deliverable | project → assemble → grade → title (Resolve) | `/hr-project` … `/hr-title` |
| deliverable | export | `/hr-export` |

Data lives in three layers, all local and never in the repo:
- **Machine:** `/hr-config`.
- **Library:** `/hr-library` covers clients, brands, players, teams and cameras. Players learn from every game.
- **Work:** under `<output>/_hr/`.

Sport rules live in `$S/../../../sports/<sport>/pack.md`; the shared quality bar is in `$S/../reference/quality-bar.md`.

## Procedure
1. **Machine check:** `hrstate.py config`. If output_folder is missing, do `/hr-config` first.
2. **Parse `$ARGUMENTS`:**
   - empty, or describes new work ("today's games", a card folder, a player and a game) → run **/hr-session**, the only place that asks questions. A single reel goes through the same flow with one game and one deliverable.
   - `status` → `hrstate.py status` and stop.
   - `resume` / `run` [session] → `hrstate.py use session <name>` if named, then go to step 3.
   - `from <stage>` [deliverable|target|game] → `hrstate.py <scope> reset <stage>`, then step 3.
3. **Run the queue.** Loop:
   ```
   python3 $S/hrstate.py next      # prints {scope, game, id, stage} and makes that unit current; null = done
   ```
   For each unit, read `hr-<stage>`'s SKILL.md (`$S/../../hr-<stage>/SKILL.md`), follow it exactly including its "Done when" checks, and mark it done in its scope (`hrstate.py [target|deliv] done <stage> "<note>"`). Then call `next` again.
   - The order is built in: every game's ingest + survey first, then each needed target's find, then deliverables by priority.
   - **Long work in the background:** survey of a large game takes minutes. Start it with `run_in_background`, and while it runs do the next unit that doesn't depend on it (another game's ingest, or a find on an already-surveyed game).
4. **Autonomy:** after the session plan is confirmed, ask no more questions. Make reasonable calls, record uncertain ones in the unit's note or `deliv.flags`, and continue. Exception: an unknown camera or a shirt that can't be calibrated blocks that game only; flag it, skip its units, and finish everything else.
5. **Context:** everything is on disk after every step. If the conversation is compacted, `hrstate.py status` + `next` resumes exactly where you were. Don't hold clip lists in memory; read them from the state files.
6. **Final report** (when `next` returns null):
   - the status board;
   - every delivered file with its client and stats;
   - per deliverable, the plays and what the camera did;
   - all flags (unconfirmed candidates, encoding mismatches, judder, offline media);
   - which player profiles learned what (new refs, cue reliability changes, look flags).

   Offer `hrstate.py clean <game>` for games whose deliverables are all exported.

If a unit fails in a way you can't fix, flag it, leave it not-done, continue with units that don't depend on it, and give the user the exact command to resume (`/highlight-reel resume`).

## Improving the skill
Each stage doc ends with "Known gaps"; that's the roadmap. When a run teaches something about a sport, put it in that sport's pack.md. If it's about a stage, put it in the stage doc. If it's about a player, team or camera, it goes in their profile, never in the repo.
