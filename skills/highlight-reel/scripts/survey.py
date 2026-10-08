"""Survey every usable clip (segment) of the current game: 5 frames at 10/25/50/75/90% of the segment
(frames/<clip>/ 1280w, frames_4k/<clip>/ full-res) and 2 fps thumbnails over the segment (src2fps/<clip>/).

Usage: python3 survey.py [--only CLIP...] [--keep]
  Runs `cameras.py assign` first if the game has no clips yet; skips clips with use=false (export renders)
  and clips already surveyed (unless they're listed with --only). --keep keeps old output for other clips.
"""
import os, shutil, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hrstate

FF = hrstate.tool('ffmpeg')
FR, F4, S2 = hrstate.sub('frames'), hrstate.sub('frames_4k'), hrstate.sub('src2fps')
FRACS = (0.10, 0.25, 0.50, 0.75, 0.90)


def run(args):
    subprocess.run([FF, '-nostdin', '-v', 'error', '-y'] + args, check=True)


def one(item):
    cid, c = item
    a, b = float(c.get('in', 0)), float(c.get('out') or c.get('duration') or 0)
    for d in (FR, F4, S2):
        os.makedirs(os.path.join(d, cid), exist_ok=True)
    for k, f in enumerate(FRACS):
        t = a + (b - a) * f
        big = os.path.join(F4, cid, f'frame_{k}.jpg')
        run(['-ss', f'{t:.3f}', '-i', c['path'], '-frames:v', '1', '-q:v', '2', big])
        run(['-i', big, '-vf', 'scale=1280:-2', '-q:v', '3', os.path.join(FR, cid, f'frame_{k}.jpg')])
    run(['-hwaccel', 'videotoolbox', '-ss', f'{a:.3f}', '-t', f'{b - a:.3f}', '-i', c['path'], '-an',
         '-vf', 'fps=2,scale=480:-2', '-q:v', '5', os.path.join(S2, cid, 't_%04d.jpg')])
    return cid


def main(a):
    only = a[a.index('--only') + 1:] if '--only' in a else None
    if not hrstate.get('media.clips'):
        import cameras
        cameras.assign()
    clips = {k: v for k, v in (hrstate.get('media.clips') or {}).items() if v.get('use', True)}
    unknown = [k for k, v in clips.items() if not v.get('camera')]
    if unknown:
        sys.exit(f'survey: {len(unknown)} clips from unknown cameras (e.g. {unknown[0]}) — add camera profiles first')
    if only:
        todo = {k: clips[k] for k in only}
        for k in todo:
            for d in (FR, F4, S2):
                shutil.rmtree(os.path.join(d, k), ignore_errors=True)
    else:
        if '--keep' not in a:
            for d in (FR, F4, S2):
                for k in os.listdir(d):
                    if k not in clips:
                        shutil.rmtree(os.path.join(d, k), ignore_errors=True)
        todo = {k: v for k, v in clips.items() if not os.path.exists(os.path.join(FR, k, 'frame_4.jpg'))}
    with ThreadPoolExecutor(6) as ex:
        for i, cid in enumerate(ex.map(one, todo.items()), 1):
            if i % 25 == 0:
                print(f'  {i}/{len(todo)}', flush=True)
    print(f'surveyed {len(todo)} clips ({len(clips)} usable in game) → {hrstate.game_dir()}')


if __name__ == '__main__':
    main(sys.argv[1:])
