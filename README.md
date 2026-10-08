# highlight-reel

Soccer highlight reels in DaVinci Resolve, built by [Claude Code](https://claude.com/claude-code).

Point it at a folder of raw game clips and it finds the featured player (or the whole team's best moments), picks and orders the plays, directs a 9:16 virtual camera that follows the player, then switches to the ball on shots and passes and pans back for the celebration. It then builds the Resolve timeline, grades, adds a lower third and exports. You can run it end to end with one command, or run any stage on its own.

## Commands

| Command | What | Needs Resolve |
|---|---|---|
| `/hr-config` | One-time machine setup: media root, output folder, default grade, dependency check | no |
| `/hr-profile` | Build/edit **player**, **team** and **camera** profiles | no |
| `/highlight-reel` | Full run: guided setup, then every stage autonomously. Also `status`, `resume`, `from <stage>` | — |
| `/hr-setup` | This game: player, team/kit, game folder, deliverable; detects every camera → workspace + `reel.json` | no |
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

## Three layers of data (all local — none of it is in this repo)

| Layer | Where | Set by | Holds |
|---|---|---|---|
| Machine | `~/.hr_work/config.json` | `install.sh` / `/hr-config` | media root, output folder, default `.drx`, ffmpeg |
| Profiles | `~/.hr_work/players/`, `teams/`, `cameras/` | `/hr-profile`, and updated by every reel | **player**: name, team(s) & number, hair/boots/accessories, number decoys, lower third, past games · **team**: kits with jersey colour calibrated per footage type, roster, opponents · **camera**: how to recognise its files, colour encoding |
| Game | `<output>/_hr/<team> - <event>/reel.json` | the stages | settings, found clips, picks, renders, Resolve IDs, progress |

Set `HR_HOME` to keep it somewhere other than `~/.hr_work`. See `examples/` for fictional profiles.

### Mixed cameras
A game folder can mix cameras and footage types: a mirrorless in Log, a phone in HDR (often variable frame rate, sometimes portrait), an action cam, or reels you've already exported. `cameras.py probe` recognises each clip's camera from metadata in about a second, and setup asks about any camera it doesn't know. Colour encoding, jersey-colour calibration, Resolve input colour space, reframing limits and grade checks are all handled **per clip**. Clips from `export`-type cameras are skipped.

## How stages share work

Each game gets a workspace at `<output_folder>/_hr/<team> - <event>/` containing `reel.json` (settings, found clips, selections, renders, Resolve IDs, stage progress) and its working files. Every stage reads what earlier stages wrote, so any stage can be re-run on its own. `skills/highlight-reel/scripts/hrstate.py` manages it:

```
python3 hrstate.py status            # settings + which stages are done
python3 hrstate.py list / use NAME   # switch between games
python3 hrstate.py reset grade       # redo from a stage
```

## Requirements

- Claude Code
- DaVinci Resolve (Studio for external scripting) and a DaVinci Resolve MCP server connected to Claude Code
- `ffmpeg` / `ffprobe` (found on PATH or set in config)
- Python 3 with `opencv-python numpy scipy pillow`
- Footage laid out as `<media_root>/<season>/<team>/<game>/*.mp4|mov`. Tuned on 4K 59.94 Canon Log 3; other Log formats, HLG/PQ and Rec.709 are supported encodings (`cameras.py encodings`).

## Install

**As skills (short command names, edits are live):**
```
git clone https://github.com/joshdiff/highlight-reel ~/Projects/highlight-reel
~/Projects/highlight-reel/install.sh      # checks deps, asks for your folders, links the skills
```
Then in Claude Code: `/hr-profile` to add your player, team and cameras, then `/highlight-reel`.

**As a plugin:**
```
/plugin marketplace add joshdiff/highlight-reel
/plugin install highlight-reel@joshdiff
```
Then run `/hr-config` (the plugin route doesn't run `install.sh`). As a plugin, the commands may appear namespaced (e.g. `/highlight-reel:hr-setup`). Use one install method, not both.

## Status

0.3: stages with shared state; player/team/camera profiles; per-clip handling of mixed cameras. Each stage's `SKILL.md` ends with a **Known gaps** list, which is the roadmap. Next up: scanning the 2 fps thumbnails and audio peaks to rank clips (survey/find), and tracker-assisted keyframes for the virtual camera (direct).

## License

MIT
