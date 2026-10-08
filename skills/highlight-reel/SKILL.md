---
name: highlight-reel
description: Create a soccer highlight reel in DaVinci Resolve end to end — guided setup, then every stage autonomously (survey → find → select → direct → project → assemble → grade → title → export). Also "status", "resume", or "from <stage>". Each stage is its own command (/hr-setup … /hr-export).
---

# Highlight reel — full run

$ARGUMENTS

The reel is built by ten stage skills that share one per-game workspace and its `reel.json`. This command runs them in order; each one can also be run on its own (`/hr-grade` to redo just the grade, etc.).

Data lives in three layers, all local (never in the repo):
- **Machine** — `/hr-config` (or `install.sh`): media root, output folder, default grade, ffmpeg.
- **Profiles** — `/hr-profile`: players (team & number, look, decoys, lower third), teams (kits + calibrated jersey colour per footage encoding, roster, opponents), cameras (how to recognise each camera's clips, its colour encoding). A game can mix cameras; everything colour-related is decided per clip.
- **Game** — `reel.json` in the game workspace, written by the stages below.

| # | Stage | Command | Needs Resolve | Produces (in reel.json) |
|---|---|---|---|---|
| 1 | Setup | `/hr-setup` | no | `settings.*`, the workspace |
| 2 | Survey | `/hr-survey` | no | frames, sheets, `media.clips`, `calibration` |
| 3 | Find | `/hr-find` | no | `find.clips` (ID status + scored action windows) |
| 4 | Select | `/hr-select` | no | `select` (teaser, sequence, finale) |
| 5 | Direct | `/hr-direct` | no | shot lists, `_vc.mov` reframes, `direct.renders` |
| 6 | Project | `/hr-project` | yes | `resolve.project`, colour science, bins, `resolve.media_ids` |
| 7 | Assemble | `/hr-assemble` | yes | `resolve.timelines`, `resolve.items` |
| 8 | Grade | `/hr-grade` | yes | `grade` |
| 9 | Title | `/hr-title` | yes | `title` |
| 10 | Export | `/hr-export` | yes | `export` (verified file) |

`S=$(dirname "$(find -L ~/.claude/skills ~/.claude/plugins -name hrstate.py -path '*highlight-reel/scripts/*' 2>/dev/null | head -1)")` (this skill's `scripts/` folder) — `python3 $S/hrstate.py` is the state tool (`status`, `use`, `list`, `get`, `set`, `merge`, `done`, `reset`; run it with no args for help).

## Procedure

1. Read `$S/../reference/quality-bar.md`. If `hrstate.py config` has no media_root, do `/hr-config` first.
2. Parse `$ARGUMENTS`:
   - empty, or describes a new reel → run **hr-setup** (the only stage that asks questions).
   - `status` → `hrstate.py status` and stop.
   - `resume` / `continue` [game] → `hrstate.py use <game>` if named, then start at the first stage not marked done.
   - `from <stage>` [game] → `hrstate.py reset <stage>` (clears that stage and every later one), then run from it.
3. For each stage from the starting point: read the `hr-<stage>` skill's SKILL.md (`$S/../../hr-<stage>/SKILL.md`) and follow it exactly, including its "Done when" checks, then `hrstate.py done <stage> "<one-line note>"`. Proceed to the next stage without asking.
4. After setup, work autonomously to the end — no more questions. Make reasonable calls and continue; record uncertain calls in the stage note so the final report can list them.
5. Skip stages that don't apply (hr-direct renders only for social_reel — for 16:9 deliverables it still decides windows; see its doc).
6. Final report (after hr-export): output file and ffprobe stats; each clip with its beat (e.g. "take-on past #4, 7s") and what the camera did; anything uncertain (e.g. a CANDIDATE you couldn't confirm); then the profile updates (see hr-export).

If a stage fails in a way you can't fix, stop, leave the earlier stages marked done, and tell the user the exact command to resume (`/highlight-reel resume`).

## Improving the skill
Each stage doc ends with "Known gaps" — the next things to optimize. When a run teaches something new (a missed clip, a grade fix, an API quirk), put the lesson in that stage's doc, not here.
