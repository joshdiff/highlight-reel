# highlight-reel

Soccer highlight reels in DaVinci Resolve, built by [Claude Code](https://claude.com/claude-code).

Point it at a folder of raw game clips and it finds the featured player (or the whole team's best moments), picks and orders the plays, directs a 9:16 virtual camera that follows the player, then switches to the ball on shots and passes and pans back for the celebration. It then builds the Resolve timeline, grades, adds a lower third and exports. You can run it end to end with one command, or run any stage on its own.

## Commands

| Command | Stage | Needs Resolve |
|---|---|---|
| `/highlight-reel` | Full run: guided setup, then every stage autonomously. Also `status`, `resume`, `from <stage>` | — |
| `/hr-setup` | Guided setup (pick-lists) → per-game workspace + `reel.json` | no |
| `/hr-survey` | Frame extraction, jersey-colour detection, contact and ID sheets | no |
| `/hr-find` | Identify the player by number (rejecting decoys) or find team moments; score each play | no |
| `/hr-select` | Teaser → sequences → full-goal finale, timed to the deliverable | no |
| `/hr-direct` | Shot lists + `vcam.py` virtual-camera render (follow player → ball → back to scorer) | no |
| `/hr-project` | Resolve project, colour management, bins, import | yes |
| `/hr-assemble` | Selects and delivery timelines | yes |
| `/hr-grade` | Power-grade DRX, CDL, luma/saturation/clipping checks | yes |
| `/hr-title` | Lower third | yes |
| `/hr-export` | Render, verify, report | yes |

Deliverables: `social_reel` (1080×1920, ~45s), `recruiting_tape` (1920×1080, 2–3 min), `goals_reel` (1920×1080). Modes: one featured player, or the full team.

## How stages share work

Each game gets a workspace at `<output_folder>/_hr/<team> - <event>/` containing `reel.json` (settings, found clips, selections, renders, Resolve IDs, stage progress) and its working files. Every stage reads what earlier stages wrote, so any stage can be re-run on its own. `skills/highlight-reel/scripts/hrstate.py` manages it:

```
python3 hrstate.py status            # settings + which stages are done
python3 hrstate.py list / use NAME   # switch between games
python3 hrstate.py reset grade       # redo from a stage
```

Machine-specific defaults (media root, output folder, power-grade `.drx`, camera) go in `~/.hr_work/config.json`. `/hr-setup` asks for them on first run.

## Requirements

- Claude Code
- DaVinci Resolve (Studio for external scripting) and a DaVinci Resolve MCP server connected to Claude Code
- `ffmpeg` / `ffprobe` at `/opt/homebrew/bin/` (macOS Homebrew)
- Python 3 with `opencv-python numpy scipy pillow`
- Footage laid out as `<media_root>/<season>/<team>/<game>/*.mp4`. Tuned on 4K 59.94 Canon Log 3; Sony S-Log3 and Rec.709 are supported settings.

## Install

**As skills (short command names, edits are live):**
```
git clone https://github.com/joshdiff/highlight-reel ~/Projects/highlight-reel
~/Projects/highlight-reel/install.sh
```

**As a plugin:**
```
/plugin marketplace add joshdiff/highlight-reel
/plugin install highlight-reel@joshdiff
```
As a plugin, the commands may appear namespaced (e.g. `/highlight-reel:hr-setup`). Use one install method, not both.

## Status

0.2: the pipeline is split into stages, with shared state. Each stage's `SKILL.md` ends with a **Known gaps** list, which is the roadmap. Next up: scanning the 2 fps thumbnails and audio peaks to rank clips (survey/find), and tracker-assisted keyframes for the virtual camera (direct).

## License

MIT
