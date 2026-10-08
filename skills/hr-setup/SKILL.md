---
name: hr-setup
description: Quick path for ONE reel — one game, one player or team, one deliverable — with pick-lists (existing players most recent first, or add a new one). Builds a one-game session and hands it to /highlight-reel. For a day with several games, teams or clients use /hr-session.
---

# hr-setup — one quick reel

$ARGUMENTS

This is `/hr-session` with everything sized to one: one game, one target, one deliverable. Follow `hr-session`'s SKILL.md (`$S/../../hr-session/SKILL.md`, with `S=$(dirname "$(find -L ~/.claude/skills ~/.claude/plugins -name hrstate.py -path '*highlight-reel/scripts/*' 2>/dev/null | head -1)")`) with these shortcuts:
- **Round 1:**
  - Reel type: Player / Full team.
  - Deliverable: Social reel 9:16 / Recruiting tape / Scoring reel / Season reel.
  - Player: `hrprofile.py list players --recent` (top 3 as "Name #N (Team) — last <date>") + "Add new player". Team mode: the team instead.
- **Round 2:**
  - Game folder: the 3 newest folders for that player's/team's team media folder, labelled with the event.
  - Finish: "Finished files (ffmpeg)" (recommended) / "Grade in DaVinci Resolve".
  - Unknown cameras, as in hr-session step 2.
- The session is named `<date> <who>`; the deliverable gets priority 1, client and brand from the player's/team's `client_id`.
- After "Start", continue straight into `/highlight-reel run`, with no more questions.
