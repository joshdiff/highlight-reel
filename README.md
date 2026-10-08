# highlight-reel

Sports highlight reels for videographers, built by [Claude Code](https://claude.com/claude-code).

Film a day of games for any number of teams. In one sitting, highlight-reel then:
- finds each player (or each team's best moments) in the full-game footage;
- picks and orders the plays;
- directs a virtual camera that follows the player, switches to the ball on shots and passes, and pans back for the celebration;
- grades, brands and exports a reel for every client, in every aspect ratio they need.

Player profiles get smarter with every game: reference photos, which identifying cues proved reliable, how they play, and what the client asked to keep or drop.

- **Sports:** soccer, basketball, volleyball (sport packs in `sports/`; add more the same way)
- **Footage:** short clips, long continuous recordings, AI-camera full matches; any camera mix in one game (Canon/Sony/Panasonic Log, iPhone HDR/Apple Log, GoPro, DJI, Veo/Trace/Pixellot)
- **Finishing:** ffmpeg (no editing app needed), DaVinci Resolve (via its MCP server), or an FCPXML handoff to Final Cut / Premiere
- **Deliverables:** social reel, recruiting tape, scoring reel, season reel. Any of 9:16, 1:1, 4:5, 16:9.

## How it works

```
/hr-session  — plan the day: game folders → cameras → teams → orders (the only step that asks questions)
/highlight-reel run — processes the queue on its own, resumable:

  per game        ingest (cameras, long-file segmentation) → survey (frames, shirt colours, detection)   — once
  per target      find (a player or team; scores every play; teaches the player profile)                — once
  per deliverable select → direct (virtual camera) → finish (ffmpeg) or Resolve → export (named per client)
```

| Command | What |
|---|---|
| `/hr-config` | One-time machine setup and dependency check |
| `/hr-library` | Clients, brands, players, teams, cameras (`/hr-profile` is an alias) |
| `/hr-session` | Plan a day: several games, teams, players, clients |
| `/hr-setup` | Quick path: one game, one reel |
| `/highlight-reel` | Run / resume the queue; `status`; `from <stage>` |
| `/hr-ingest`, `/hr-survey` | Game stages |
| `/hr-find` | Target stage |
| `/hr-select`, `/hr-direct`, `/hr-finish`, `/hr-export` | Deliverable stages (ffmpeg path) |
| `/hr-project`, `/hr-assemble`, `/hr-grade`, `/hr-title` | Deliverable stages (Resolve path) |

## Player profiles that learn
Each processed game adds to a player's profile:
- **Reference photos:** confirmed sightings, per kit. The next game's identification compares against them.
- **Cue reliability:** e.g. "boots identified her in 86% of sightings, the number in 43%". Identification checks the strongest cue first.
- **Dated look observations:** a haircut or a new number gets flagged instead of silently trusted.
- **Play style:** event tallies, strong foot, positions. Recruiting tapes lean on strengths.
- **Game history:** best clips and delivered files. This is the source of season reels.
- **Client feedback:** "no defensive clips", "always include assists". Every later selection obeys it.

When you plan a new game, existing players are offered most recent first, or you add a new one.

## Your data stays local
| Layer | Where | Holds |
|---|---|---|
| Machine | `~/.hr_work/config.json` | output folder, media root, default grade, ffmpeg |
| Library | `~/.hr_work/library/` | clients, brands (+ logo, fonts, music, bumpers), players (+ reference photos), teams, cameras |
| Work | `<output>/_hr/` | sessions, games (shared survey), targets, deliverables |

Nothing personal is in this repo. `examples/` has fictional samples of each profile type. Set `HR_HOME` to keep the library elsewhere.

## Requirements
- Claude Code
- `ffmpeg`/`ffprobe` with `lut3d`, `loudnorm`, `sidechaincompress` (Homebrew's build has them)
- Python 3 with `opencv-python numpy scipy pillow`
- Optional: DaVinci Resolve (Studio for external scripting) + a DaVinci Resolve MCP server, for the Resolve path

Colour: Log and HDR footage is converted with built-in transforms generated from the manufacturers' published curves and gamuts (`skills/highlight-reel/scripts/luts.py`). If you set an official manufacturer LUT on a camera profile, it takes priority. Add a creative LUT per brand for a house look.

## Install

**As skills (short command names, edits are live):**
```
git clone https://github.com/joshdiff/highlight-reel ~/Projects/highlight-reel
~/Projects/highlight-reel/install.sh      # checks deps, migrates old data, asks for your folders, links the skills
```
**As a plugin:**
```
/plugin marketplace add joshdiff/highlight-reel
/plugin install highlight-reel@joshdiff
```
Then run `/hr-config`. Plugin commands may appear namespaced (e.g. `/highlight-reel:hr-session`). Use one install method, not both.

Then: `/hr-library` (add a client, brand, team, players, cameras) → `/hr-session`.

## Status
1.0. Each stage's `SKILL.md` ends with **Known gaps** (the roadmap).

What's been tested:
- **Real soccer footage** (Canon Log 3 clips mixed with previously exported reels): camera detection, survey, player learning, the virtual camera in all four aspects, and branded ffmpeg finishing.
- **Long-recording segmentation, on a synthetic stand-in only:** a real game's clips joined in shooting order, with the real gaps filled by a held frame and quiet noise. It covered all four of the game's best plays, but only by selecting about half the file. Only 78% of the selected time was real play, against 72% for random picks, so ranking quality is **not** established. A real continuous recording is needed to evaluate it; the best test is a camera left rolling for a half while short clips of the same game are shot for comparison.

**Not yet tested on** real basketball/volleyball footage, phone HDR clips, or AI-camera exports: those packs and presets are written from each sport's and vendor's conventions and will be tuned on first use. The FCPXML handoff is well-formed but hasn't been test-imported into Final Cut or Premiere.

## License
MIT
