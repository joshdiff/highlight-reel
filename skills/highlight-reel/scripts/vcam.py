"""Virtual camera: the operator-style framing path of a play, from a shot list.

Usage: python3 vcam.py shotlist.json            render the reframe (ffmpeg path; scratch, <deliverable>/reframes/)
       python3 vcam.py shotlist.json --check    framing check only: 4 fps contact sheet into <deliverable>/checks/
                                                (renders a small preview in scratch and deletes it)
       python3 vcam.py shotlist.json --keys     print the Resolve keyframes (Pan/Tilt/Zoom) it would get

The same path drives both routes: the Resolve path never renders — timeline_export.py turns plan() into
Inspector Pan/Tilt/Zoom keyframes on the ORIGINAL clip, trimmed in the timeline; the ffmpeg path renders
it here into <deliverable>/reframes/ (scratch, deleted when the session is cleaned).

shotlist.json:
{
  "src": "R7__1630",                        # clip/segment id (looked up in game.json) or a path
  "out": "/path/R7__1630_vc.mov",           # optional; default <deliverable>/reframes/<shotlist name>_vc.mov
  "in": 2.6, "out_t": 10.8,                # source seconds
  "keys": [                                 # x: 0-100 across source width (vgrid ruler)
    {"t": 2.6, "x": 33, "zoom": 1.0, "subject": "player", "event": "possession"},
    {"t": 4.2, "x": 62, "zoom": 1.0, "subject": "ball", "event": "shot", "move": "fast"},
    ...
  ],
  "y": 55,                                  # optional default vertical centre 0-100 (default 50);
                                            # any key may carry its own "y" (e.g. volleyball attacks)
  "freeze": {"t": 4.5, "dur": 1.5},         # optional: hold this source time (cold-open teaser)
  "whip_out": true,                         # optional: horizontal blur ramp on the last 0.2s
  "handles": 0.2,                           # optional: extra source seconds each side for transitions
                                            # (clamped to the file; the actual values are printed)
  "follow": {"deadzone": 0.18}              # optional overrides of FOLLOW, or false for raw keys
}
zoom 1.0 = full-height 9:16 window (the default — keep the game's context); 1.1 at most for a tiny
subject (capped at 1.5 for 4K sources, 1.15 for <=1080p; portrait sources are already 9:16 — zoom/pan
only). Zoom is smoothed over 1s. move "fast" = whip to that key (shot/pass); otherwise the window
follows like an operator (dead zone, eased spring, speed limits — see follow()), not like the keys.
Output: ProRes 422 HQ 10-bit, Log preserved (no colour change), audio PCM.
"""
import json, sys, subprocess, os, shutil
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hrstate

FF = hrstate.tool('ffmpeg'); FP = hrstate.tool('ffprobe')
OUT_SIZES = {'9:16': (1080, 1920), '1:1': (1080, 1080), '4:5': (1080, 1350), '16:9': (1920, 1080)}


def probe(src):
    v = json.loads(subprocess.run([FP, '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                                   'stream=width,height,avg_frame_rate,r_frame_rate', '-of', 'json', src],
                                  capture_output=True, text=True).stdout)['streams'][0]
    n, d = (v.get('avg_frame_rate') or v['r_frame_rate']).split('/')
    if not float(d) or not float(n):
        n, d = v['r_frame_rate'].split('/')
    return int(v['width']), int(v['height']), float(n) / float(d)


def path(keys, t0, t1, fps, y_default=50):
    """Per-frame (x, y, zoom). Smooth keys ease with smoothstep; 'fast' keys whip to the new subject in
    <=0.25s. A light 0.2s smoothing removes keyframe kinks everywhere EXCEPT inside whips (keeps them crisp)."""
    keys = sorted(keys, key=lambda k: k['t'])
    for k in keys:
        k.setdefault('y', y_default); k.setdefault('zoom', 1.0)
    ts = np.arange(t0, t1, 1.0 / fps)
    out = np.empty((len(ts), 3)); whip = np.zeros(len(ts), bool)
    for i, t in enumerate(ts):
        if t <= keys[0]['t']:
            out[i] = keys[0]['x'], keys[0]['y'], keys[0]['zoom']; continue
        if t >= keys[-1]['t']:
            out[i] = keys[-1]['x'], keys[-1]['y'], keys[-1]['zoom']; continue
        j = max(k for k in range(len(keys)) if keys[k]['t'] <= t)
        a, b = keys[j], keys[j + 1]
        u = (t - a['t']) / (b['t'] - a['t'])
        if b.get('move') == 'fast':          # reach the new subject in <=0.25s, then track
            span = b['t'] - a['t']; u = min(1.0, u * span / min(span, 0.25))
            whip[i] = u < 1.0
        u = u * u * (3 - 2 * u)              # smoothstep ease in/out
        out[i] = [a[c] + (b[c] - a[c]) * u for c in ('x', 'y', 'zoom')]
    k = max(1, int(fps * 0.2)) | 1; pad = k // 2
    sm = np.stack([np.convolve(np.pad(out[:, c], pad, mode='edge'), np.ones(k) / k, mode='valid')
                   for c in range(3)], axis=1)
    sm[whip] = out[whip]
    return ts, sm[:, 0], sm[:, 1], sm[:, 2], whip


FOLLOW = {'deadzone': 0.18, 'freq': 1.4, 'vmax': 120.0, 'amax': 400.0, 'soft': 0.22, 'margin': 0.38}


def follow(xs, whip, win, fps, p):
    """Move the window like a camera operator, not like the detections: the subject may drift inside a
    dead zone (deadzone × window width either side of centre) without the window moving; outside it the
    window eases after them on a critically damped spring (freq Hz), with speed (vmax) and acceleration
    (amax) limits in source-width units per s / s². Hard rule: the subject never gets further than
    margin × window width from centre (≈ inside the middle 76%). Whips ('fast' keys) pass through untouched.
    win = window width per frame in the same 0–100 units."""
    tgt = xs.copy(); n = len(xs); dt = 1.0 / fps
    k = max(1, int(fps * 0.5)) | 1                     # 0.5s centred pre-smoothing removes detection jitter
    sm = np.convolve(np.pad(tgt, k // 2, mode='edge'), np.ones(k) / k, mode='valid')
    look = max(0, int(fps * 0.15))                     # aim slightly ahead so the spring's lag cancels
    sm = np.concatenate([sm[look:], np.repeat(sm[-1], look)]) if look else sm
    w = 2 * np.pi * p['freq']; c, v = sm[0], 0.0; cam = np.empty(n)
    for i in range(n):
        if whip[i]:
            c, v = xs[i], 0.0; cam[i] = c; continue
        e = sm[i] - c; dz = p['deadzone'] * win[i]
        e = 0.0 if abs(e) < dz else e - np.sign(e) * dz
        edge = max(0.0, abs(xs[i] - c) / win[i] - p.get('soft', 0.26)) / 0.12   # 0 → 1 as they near the margin
        we = w * (1 + 2 * min(edge, 1.0))                  # stiffen near the edge so the hard limit rarely fires
        a = np.clip(we * we * e - 2 * we * v, -p['amax'], p['amax'])
        v = np.clip(v + a * dt, -p['vmax'], p['vmax']); c += v * dt
        lim = p['margin'] * win[i]                     # never lose the subject
        if xs[i] - c > lim:
            c = xs[i] - lim
        elif c - xs[i] > lim:
            c = xs[i] + lim
        cam[i] = c
    return cam


def plan(spec_path):
    """The framing path, no rendering: per source frame from t0 (in − handle) to t1 (out + handle), the
    crop window (cx, cy = centre, cw × ch, source pixels; always inside the frame) of the output aspect."""
    s = json.load(open(spec_path))
    s['clip'] = s['src']
    if not os.path.exists(s['src']):   # a clip/segment id of the current game
        s['src'] = hrstate.get(f"media.clips.{s['src']}.path") or sys.exit(f"unknown clip {s['src']}")
    W, H, fps = probe(s['src'])
    dur = float(subprocess.run([FP, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', s['src']],
                               capture_output=True, text=True).stdout.strip() or 1e9)
    hd = float(s.get('handles', 0))                    # extra source seconds each side, for transitions
    h_in, h_out = min(hd, s['in']), min(hd, max(0.0, dur - s['out_t'] - 0.05))
    if s.get('freeze'):
        h_out = 0.0                                    # a freeze is its own tail
    t0, t1 = s['in'] - h_in, s['out_t'] + h_out
    if s.get('freeze'):
        t1 = max(t1, s['freeze']['t'])
    ts, xs, ys, zs, whip = path(s['keys'], t0, t1, fps, s.get('y', 50))
    # Output aspect (9:16 default). The zoom-1.0 window is the largest window of that aspect inside the
    # source, so portrait phone clips, 4K and HD all work. Zoom is capped by how far the crop can shrink
    # before the upscale gets soft: crop height may go down to ~0.75 of the output height (1.15–2.0).
    aw, ah = (int(v) for v in s.get('aspect', '9:16').split(':'))
    OW, OH = OUT_SIZES.get(f'{aw}:{ah}', (1080, round(1080 * ah / aw / 2) * 2))
    ar = aw / ah
    base_h = H if W / H > ar else W / ar
    zmax = min(2.0, max(1.15, base_h / OH * 1.33))
    zs = np.clip(zs, 1.0, zmax)
    k = max(1, int(fps * 1.0)) | 1                     # zoom changes slowly: 1s smoothing
    zs = np.convolve(np.pad(zs, k // 2, mode='edge'), np.ones(k) / k, mode='valid')
    if s.get('follow', True) is not False:
        p = dict(FOLLOW, **(s['follow'] if isinstance(s.get('follow'), dict) else {}))
        win = 100.0 * (base_h / zs) * ar / W
        xs = follow(xs, whip, win, fps, p)
        ys = follow(ys, whip, 100.0 * (base_h / zs) / H, fps, dict(p, deadzone=0.25, vmax=20.0))
    wins = []
    for x, yv, z in zip(xs, ys, zs):
        ch = base_h / z; cw = ch * ar
        cx = min(max(x / 100.0 * W, cw / 2), W - cw / 2)   # clamp: never show black edges
        cy = min(max(yv / 100.0 * H, ch / 2), H - ch / 2)
        wins.append((cx, cy, cw, ch))
    return {'spec': s, 'src': s['src'], 'W': W, 'H': H, 'fps': fps, 't0': t0, 't1': t1, 'h_in': h_in,
            'h_out': h_out, 'ts': ts, 'wins': wins, 'whip': whip, 'out_size': (OW, OH), 'ar': ar}


def resolve_keys(pl, tl_size=None, tol_px=3.0):
    """plan() → Inspector keyframes for the original clip in a timeline of tl_size (default the output size),
    with Resolve's default "scale entire image to fit": [{t (source s), pan, tilt (timeline px), zoom}].
    Pan/Tilt move the window centre to the frame centre; zoom is relative to fit. The per-frame path is
    reduced to the fewest keys that stay within tol_px of it (linear between keys), so the clip carries a
    handful of editable keys, not one per frame; whip frames are always kept."""
    TW, TH = tl_size or pl['out_size']; W, H = pl['W'], pl['H']
    fit = min(TW / W, TH / H)
    rows = []
    for t, (cx, cy, cw, ch), wh in zip(pl['ts'], pl['wins'], pl['whip']):
        S = TH / ch if cw / ch <= TW / TH else TW / cw          # source px → timeline px for this window
        rows.append((float(t), -(cx - W / 2) * S, (cy - H / 2) * S, S / fit, bool(wh)))
    if not rows:
        return []
    keep = _rdp(rows, 0, len(rows) - 1, tol_px, {0, len(rows) - 1})
    keep |= {i for i, r in enumerate(rows) if r[4]} | {i + 1 for i, r in enumerate(rows[:-1]) if r[4]}
    return [{'t': round(rows[i][0], 4), 'pan': round(rows[i][1], 2), 'tilt': round(rows[i][2], 2),
             'zoom': round(rows[i][3], 4)} for i in sorted(keep)]


def _rdp(rows, a, b, tol, keep):
    """Ramer–Douglas–Peucker over (pan, tilt, zoom·1000) against time; iterative to avoid deep recursion."""
    stack = [(a, b)]
    while stack:
        a, b = stack.pop()
        if b - a < 2:
            continue
        ta, tb = rows[a][0], rows[b][0]; worst, wi = 0.0, None
        for i in range(a + 1, b):
            u = (rows[i][0] - ta) / (tb - ta) if tb > ta else 0
            e = max(abs(rows[i][c] - (rows[a][c] + (rows[b][c] - rows[a][c]) * u)) * (1000 if c == 3 else 1)
                    for c in (1, 2, 3))
            if e > worst:
                worst, wi = e, i
        if worst > tol:
            keep.add(wi); stack += [(a, wi), (wi, b)]
    return keep


def main(spec_path, check=False):
    pl = plan(spec_path); s = pl['spec']; W, H, fps = pl['W'], pl['H'], pl['fps']
    t0, t1, h_in, h_out, ts = pl['t0'], pl['t1'], pl['h_in'], pl['h_out'], pl['ts']
    stem = os.path.splitext(os.path.basename(spec_path))[0]
    tmp = hrstate.tmp('vcam')
    if check:
        s['out'] = os.path.join(tmp, stem + '_preview.mp4')
    elif not s.get('out'):
        s['out'] = os.path.join(hrstate.dsub('reframes'), stem + '_vc.mov')
    OW, OH = pl['out_size']
    if check:
        OW, OH = OW // 3 // 2 * 2, OH // 3 // 2 * 2
    cmds = []
    for i, (cx, cy, cw, ch) in enumerate(pl['wins']):
        ch = int(round(ch / 2) * 2); cw = int(round(cw / 2) * 2)
        x0 = min(max(cx - cw / 2, 0), W - cw); y0 = min(max(cy - ch / 2, 0), H - ch)
        cmds.append(f'{i / fps:.4f} crop w {cw}, crop h {ch}, crop x {int(x0)}, crop y {int(y0)};')
    cf = os.path.join(tmp, 'cmds.txt'); open(cf, 'w').write('\n'.join(cmds))
    first = cmds[0].split(' ', 1)[1]
    w0 = int(first.split('crop w ')[1].split(',')[0]); h0 = int(first.split('crop h ')[1].split(',')[0])
    rng = subprocess.run([FP, '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=color_range',
                          '-of', 'csv=p=0', s['src']], capture_output=True, text=True).stdout.strip()
    in_rng = 'full' if rng == 'pc' else 'tv'   # Canon R7 HEVC is full range; ProRes out is video range
    vf = [f"sendcmd=f='{cf}'", f'crop={w0}:{h0}:0:0',
          f'scale={OW}:{OH}:flags=lanczos:in_range={in_rng}:out_range=tv', 'setsar=1']
    fr = s.get('freeze')
    if fr:   # hold one frame (teaser cliffhanger): cut at freeze t, pad with clones
        dur_keep = fr['t'] - t0
        vf.append(f"trim=duration={dur_keep:.4f},tpad=stop_mode=clone:stop_duration={fr['dur']}")
    if s.get('whip_out'):
        total = (fr['t'] - t0 + fr['dur']) if fr else (t1 - t0)
        st = total - 0.2
        vf.append(f"gblur=sigma=40:sigmaV=0.01:enable='gte(t,{st:.3f})'")
    os.makedirs(os.path.dirname(s['out']), exist_ok=True)
    codec = (['-c:v', 'libx264', '-crf', '26', '-preset', 'veryfast', '-pix_fmt', 'yuv420p'] if check else
             ['-c:v', 'prores_ks', '-profile:v', '3', '-pix_fmt', 'yuv422p10le'])
    cmd = [FF, '-nostdin', '-v', 'error', '-y', '-ss', str(t0), '-t', str(t1 - t0), '-i', s['src'],
           '-vf', ','.join(vf)] + codec + ['-c:a', 'pcm_s16le' if not check else 'aac', s['out']]
    if fr:
        cmd[cmd.index('-c:a'):cmd.index('-c:a')] = ['-af', f"apad,atrim=duration={fr['t'] - t0 + fr['dur']:.4f}"]
    subprocess.run(cmd, check=True)
    if check:   # the sheet is the only thing kept
        rows = max(1, -(-int((t1 - t0) * 4) // 8))
        sheet = os.path.join(hrstate.dsub('checks'), stem + '.jpg')
        subprocess.run([FF, '-nostdin', '-v', 'error', '-y', '-i', s['out'], '-vf',
                        f'fps=4,scale=270:-2,tile=8x{rows}', '-frames:v', '1', sheet], check=True)
        shutil.rmtree(tmp, ignore_errors=True)
        print(sheet, f'{len(ts)} frames @ {fps:.2f}', f'{len(resolve_keys(pl))} Resolve keys')
        return
    shutil.rmtree(tmp, ignore_errors=True)
    print(s['out'], f'{len(ts)} frames @ {fps:.2f}', json.dumps({'handle_in_s': round(h_in, 4), 'handle_out_s': round(h_out, 4)}))


if __name__ == '__main__':
    if '--keys' in sys.argv:
        pl = plan(sys.argv[1]); ks = resolve_keys(pl)
        print(json.dumps({'src': pl['src'], 't0': pl['t0'], 't1': pl['t1'], 'frames': len(pl['ts']),
                          'keys': len(ks), 'first': ks[:3], 'last': ks[-2:]}, indent=1))
    else:
        main(sys.argv[1], check='--check' in sys.argv)
