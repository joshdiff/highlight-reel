# What "great" looks like — rules for every sport

Learned by comparing an automated reel with a hand-cut one. The skill must reach this bar on its own; it never takes the user's own cut as an input. Sport-specific rules (events, scoring, director table, reel timings) live in the sport pack: `sports/<sport>/pack.md` + `pack.json` (`python3 $S/sports.py show <sport>`).

## Craft rules (all sports)
- **On the ball, making something happen.** Player reels show the featured player driving the play. Team reels show the team's best moments with screen time spread across players. No scrambles the player isn't driving, and no distant shots where they're tiny.
- **Structure:**
  1. Open strong, with the name lower third. A freeze-frame cold-open teaser (best scoring play frozen before the outcome, whip out) is optional — only when there's a goal/score worth holding back; otherwise open straight on the strongest play.
  2. Varied-length sequences, strongest first.
  3. If there was a teaser, that play in full at the end, through the reaction/celebration.
- **The frame is directed.** It follows the player while they have the ball, switches to the ball the instant they shoot/pass/attack, holds on the outcome, then pans back to the scorer and stays through the celebration. It does not punch in: zoom stays at 1.0.
- **Consistent output.** Every play and every game lands on the same look: a correction is solved per clip (look.py) against a fixed neutral-standard target anchored on the playing surface, so sun, cloud and camera differences don't show. No fixed creative grade by default.
- **Natural grade — it should look real.** No clipped sky or gym lights, shirts their true colour (a pale kit stays pale), grass green but not neon. Measured: mean luma 0.36–0.45, under 0.5% of pixels at extreme saturation ("vivid"), clipped <1%. Never push saturation to hit a number; an overcast day looks overcast.
- **Wide, calm framing.** 9:16 from 16:9 already crops to a third of the width, so keep zoom at 1.0 and let the viewer see the play around the player. The window moves like a camera operator: still while the player stays near centre, eased when it has to follow, never jittering with the detections.
- **Every claim is verified on rendered frames,** not on settings read back.

## Modes and deliverables
- PLAYER targets feature one player ("the player" / "they" in the docs).
- TEAM targets feature a team: "the player" becomes whichever player of that team has the ball or makes the play, and the scorer is whoever scored.

Deliverable types (timings per sport in `pack.json → deliverables`):

| type | default aspect | what |
|---|---|---|
| social_reel | 9:16 | [teaser →] sequences [→ full teaser play] |
| recruiting_tape | 16:9 | grouped by skill for coaches |
| scoring_reel (`goals_reel` alias) | 16:9 | every scoring play, chronological |
| season_reel | 9:16 | best clips across a player's games (from their profile) |

A deliverable can request several aspects (9:16, 1:1, 4:5, 16:9); each gets its own render.

## Data layers (all local; nothing personal goes in the repo)
- **Machine:** `hrstate.py config` (output folder, media root, default grade, ffmpeg).
- **Library:** `hrprofile.py` (players, teams), `cameras.py` (cameras). Players learn after every game; see `/hr-library`.
- **Work:** `<output>/_hr/` holding sessions, games (shared survey), targets (find per player/team) and deliverables (select → export). `python3 $S/hrstate.py status` shows the board.

## Environment facts
- Scripts: the highlight-reel skill's `scripts/` folder (`$S`, located by the `find` one-liner at the top of each stage). Run python WITHOUT `-I` (cv2/scipy live in user site-packages). ffmpeg/ffprobe via `hrstate.tool()`.
- Use python, never `bc`, for timestamp maths (bc drops the leading zero and ffmpeg rejects ".29").
- A game can mix cameras and footage types. Camera, encoding, orientation, fps and VFR are per clip in `media.clips`; never assume one camera per game.
- Times in find/select/shot lists are SOURCE-FILE seconds (absolute in the file), even for segments of long files.
- Resolve 21.1 via the davinci-resolve MCP: Pan keyframes are unavailable (`add_keyframe` → "'NoneType' object is not callable"), which is why reframing is done by `vcam.py`. Titles need the nested-timeline route (hr-title).
- If Resolve reports "Full resolution media not found" / a clip reads Offline although the file exists (e.g. renamed on disk after import), `media_pool_item` → `replace_clip` with the current path relinks it in place; the timeline items keep their trims and grades. Re-set its Input Color Space after (replace resets it to Project).
- Resolve frame captures/renders can start failing on EVERY clip with "Error decoding full resolution media for <clip>" after many captures and timeline switches, although the files decode fine with ffmpeg. Save the project, load another project, then load it back (loading the open project is a no-op) and set the delivery timeline current; captures then work.
