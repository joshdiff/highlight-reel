# Basketball pack

## What a highlight is
Scoring plays first, and how they score (variety matters), then playmaking, then defense. Possessions are short and scores are frequent, so a full game yields many candidates. Be selective: favour difficulty (contested, off the dribble, and-ones) and momentum moments (runs, buzzer-beaters).

## Finding moments
- **Makes:** ball through the hoop / net snapping (watch the rim region in the survey frames); a scoreboard change; all ten players reversing direction right after; bench/crowd reaction.
- **And-ones:** the whistle plus the shooter flexing or yelling.
- **Blocks / steals:** a sudden change of direction toward the other basket with one player out front.
- **Dead time to skip:** free-throw setups, timeouts, inbounds. They're long in continuous recordings; segmentation drops them.
- The ball colour is close to the hardwood's, so don't rely on ball detection. Follow players and the rim.

## Identification
Numbers are large on the front AND back, which makes this the most reliable sport for number ID. Secondary cues: shoes (often distinctive colours), arm/leg sleeves, headbands, hair. Home whites clip under gym lighting, so calibrate the shirt colour on a correctly exposed frame. Decoys: the same number on the other team, and similar numbers (#3/#23/#33).

## Scoring (events in pack.json)
- **3:** made three, and-one, dunk, transition score, block, steal → score, handle → score, assist
- **2:** made two, putback, steal, charge
- **1:** rebound, free throw (except clutch), off the ball

## Reel structure
- **Social:** faster than soccer: 6–10 sequences of 2–7s, 30–45s total. Teaser (optional — only for a standout scoring play; otherwise open on the best play): best dunk/three/and-one, frozen at the top of the shot with the ball in the air. Finale: that play in full, through the reaction (bench, celebration, back-pedal).
- **Recruiting:** coaches expect 3–5 min. Scoring variety (threes, pull-ups, finishes at the rim, free-throw form optional) → playmaking (passes, pick-and-roll reads) → defense (blocks, steals, charges, rotations). Keep each possession whole from the catch.
- **Scoring reel:** every make, in chronological order: touch → shot → make → reaction.

## Director rules — who the frame follows
| Moment | Subject | Framing |
|---|---|---|
| Ball-handler (dribble/drive) | PLAYER | centre on them, lead room toward the basket; zoom 1.0 (1.1 at most); keep the defender in frame on a drive |
| Crossover / move | PLAYER + defender | centre between them, keep zoom |
| SHOT (jumper / three) | PLAYER → BALL → RIM | stay on the shooter through the release; `"move":"fast"` to the rim as the ball leaves the hand (the rim is the destination, not the ball's arc); hold the rim through the make ~0.5s |
| — MAKE | RIM → SHOOTER | smooth pan back to the shooter (0.6–1.0s) for the reaction / back-pedal; end ~1.5s later |
| — MISS / BLOCK | RIM → rebound / blocker | follow the ball off the rim to the rebound; on a block, the blocker is the subject from contact |
| Drive to the rim / dunk | PLAYER (tight) | track the player into the paint, keep the rim in frame (vertical framing helps), no whip, hold through the landing |
| PASS (assist) | BALL → RECEIVER → RIM | fast to the receiver, then the shot rules above; for a passer's reel, pan back to the passer after the make if they react |
| Steal | BALL → PLAYER | centre on the deflection, then follow the player up the court |

(team) Follow the ball-handler and switch with every pass; on a make, pan to the scorer.
Vertical crops suit basketball: the rim and the shooter usually fit together at zoom 1.0.
