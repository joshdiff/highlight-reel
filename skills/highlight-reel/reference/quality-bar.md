# What "great" looks like — the bar every stage serves

Learned by comparing an automated reel with a hand-cut one. The skill must reach this bar on its own — it never takes the user's own cut as an input.

- ~40–50s, 1080×1920 @ 29.97, ~14 Mbps, natural grade (no clipped sky, true jersey colour, rich grass).
- **Structure:** cold-open TEASER of the best goal/shot (shot → ball in flight → FREEZE before the outcome, name lower third on screen, whip-blur out) → 5–8 on-ball sequences of VARIED length (3–9s) → FULL goal at the end: build-up → shot → ball in net → pan back to the scorer → celebration.
- **(player) Every clip shows the featured player on the ball** (receive → dribble → take-on → shot/pass). No scrambles they aren't driving, no distant wide shots where they're tiny.
- **(team) Every clip is a team moment worth watching:** goals (all of them), shots on target, keeper saves, take-ons, combination play (2–3 passes ending in a chance), big defensive stops. Spread screen time across players; goals and their build-up come first.
- **The frame is directed:** follows the featured player (team: the ball carrier) while they have the ball, switches to the BALL the instant they shoot or pass, holds on the outcome, PANS BACK to the scorer on a goal and stays through the celebration, widening as teammates arrive. Punches in on 1v1 take-ons.

## Modes
PLAYER mode features one player ("the featured player" / "she" in these docs). TEAM mode features the team: "the featured player" in every rule becomes *whichever team_jersey_color player has the ball or makes the play*, and the scorer is whoever scored. Rules marked (player) or (team) apply to one mode only.

## Deliverables
| deliverable_type | aspect | length | structure | render |
|---|---|---|---|---|
| social_reel | 1080×1920 | 40–50s (50–60s with several goals, team) | teaser → 5–8 sequences → full goal | 14000 kb/s, 29.97 |
| recruiting_tape | 1920×1080 | 2–3 min | goals (build-up + finish) → take-ons/skills → passing/defending | 25000 kb/s, 29.97 |
| goals_reel | 1920×1080 | as needed | every goal, chronological, build-up → finish → celebration | 20000 kb/s, 29.97 |

## Environment facts
- Scripts: the highlight-reel skill's `scripts/` folder (`$S`, located by the `find` one-liner at the top of each stage). Run python WITHOUT `-I` (cv2/scipy live in user site-packages). ffmpeg/ffprobe at `/opt/homebrew/bin/`.
- Use python, never `bc`, for timestamp maths (bc drops the leading zero and ffmpeg rejects ".29").
- Machine-local defaults (media root, output folder, power-grade .drx, camera) live in `~/.hr_work/config.json` via `hrstate.py config` — never in the skill files. Media is expected as `<media_root>/<season>/<team>/<game>/`.
- Resolve 21.1 via the davinci-resolve MCP: Pan keyframes unavailable (`add_keyframe` → "'NoneType' object is not callable") — that's why reframing is done by `vcam.py`, not Resolve. Titles need the nested-timeline route (hr-title).
