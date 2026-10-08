# Soccer pack

## What a highlight is
The featured player **on the ball** making something happen: receive → dribble → take-on → shot/pass → outcome. No scrambles they aren't driving, and no distant wide shots where they're tiny. In team reels: every goal, shots on target, keeper saves, take-ons, combination play (2–3 passes ending in a chance), and big defensive stops, with screen time spread across players.

## Finding moments
- **Goals:** ball in the net; several same-shirt players converging or hugging; a centre-circle restart in the next clip; a crowd/bench noise peak. Make sure it's OUR goal by shirt colour. Never include goals conceded, unless our keeper's save is the highlight.
- **Shots/saves:** the keeper diving, or the ball going behind for a corner.
- A clip's best moment is often at the edge of the 5 survey samples. Look at the 2 fps thumbnails before you drop a clip.

## Identification
The number is large on the back and small or illegible on the front. Front-facing frames rely on the profile's look cues (hair, sleeves, boots, build). Goalkeepers wear a different colour from their outfield teammates. Common decoys: teen numbers (#17 for #7) and the same number on the opponent.

## Scoring (events in pack.json)
- **3:** goal, assist, shot on target, take-on, save
- **2:** shot, key pass, dribble, tackle won, block, header
- **1:** off the ball, a scramble, or too far to read → drop

## Reel structure
- **Social:** cold-open teaser of the best goal: shot → ball in flight → FREEZE before the outcome, with the name lower third, whip out. Then 5–8 on-ball sequences of varied length (3–9s), strongest take-ons and shots first. End with the same goal in full: build-up → shot → net → pan back to the scorer → celebration. 40–50s.
- **Recruiting:** goals with build-up → take-ons/skills → passing → defending, 2–3 min.
- **Scoring reel:** every goal (and assist for a player), in chronological order, each as build-up → finish → celebration.

## Director rules — who the frame follows
| Moment | Subject | Framing |
|---|---|---|
| Has the ball (possession / dribble) | PLAYER | centre on them, ~8% lead room toward where they're running; zoom 1.0 (1.1 at most when they're tiny in a wide shot) |
| 1v1 take-on | PLAYER + defender | centre between them, keep zoom — the 1v1 reads better with space around it |
| SHOOTS | BALL | at the kick frame add a key with `"move":"fast"` on the ball (reach it ≤0.25s), lead toward goal, follow the ball to the outcome |
| — GOAL | BALL → NET → PLAYER | hold on the ball in the net 0.4–0.6s; smooth pan back to the scorer over ~0.8–1.2s; stay on them as they react; widen to zoom 1.0 when ≥2 teammates arrive; end 1–2s into the hug (≈3–5s after the goal) |
| — SAVE / MISS | BALL → keeper/goal | hold the save or the ball going wide ~0.5s, then end (no pan back) |
| PASSES | BALL → RECEIVER | `"move":"fast"` to the ball, follow it to the receiver, stay ~0.5–1s. ASSIST (receiver scores within ~3s): follow the ball through the finish, then pan back to the passer for the celebration if they join it. Simple pass: end 0.5s after reception, unless they run for a return ball (give-and-go); then come back to them when they receive |
| RECEIVES | BALL → PLAYER | start on the ball in flight (≤0.5s), lock onto them at first touch |
| WINS the ball | PLAYER + carrier → PLAYER | centre on the duel, then follow them once they have it |

(team) On a pass, the receiver becomes the new subject; never return to the passer. On a goal, pan back to whoever scored. On a keeper save, the keeper is the subject from the shot onward.
