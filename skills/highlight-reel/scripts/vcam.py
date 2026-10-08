"""Virtual camera: render a 9:16 reframe of a 16:9 clip from a shot list.

Usage: python3 vcam.py shotlist.json

shotlist.json:
{
  "src": "R7__1630",                        # clip/segment id (looked up in game.json) or a path
  "out": "/path/R7__1630_vc.mov",           # optional; default <deliverable>/reframed/<shotlist name>_vc.mov
  "in": 2.6, "out_t": 10.8,                # source seconds
  "keys": [                                 # x: 0-100 across source width (vgrid ruler)
    {"t": 2.6, "x": 33, "zoom": 1.35, "subject": "player", "event": "possession"},
    {"t": 4.2, "x": 62, "zoom": 1.25, "subject": "ball", "event": "shot", "move": "fast"},
    ...
  ],
  "y": 55,                                  # optional default vertical centre 0-100 (default 50);
                                            # any key may carry its own "y" (e.g. volleyball attacks)
  "freeze": {"t": 4.5, "dur": 1.5},         # optional: hold this source time (cold-open teaser)
  "whip_out": true                          # optional: horizontal blur ramp on the last 0.2s
}
zoom 1.0 = full-height 9:16 window; 1.3 = 30% tighter (capped at 1.5 for 4K sources, 1.15 for <=1080p;
portrait sources are already 9:16 — zoom/pan only). move "fast" = whip to that key
(shot/pass), default "smooth" = eased follow.
Output: ProRes 422 HQ 10-bit, Log preserved (no colour change), audio PCM.
"""
import json, sys, subprocess, os, tempfile
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
    return ts, sm[:, 0], sm[:, 1], sm[:, 2]


def main(spec_path):
    s = json.load(open(spec_path))
    if not os.path.exists(s['src']):   # a clip/segment id of the current game
        s['src'] = hrstate.get(f"media.clips.{s['src']}.path") or sys.exit(f"unknown clip {s['src']}")
    if not s.get('out'):
        name = os.path.splitext(os.path.basename(spec_path))[0] + '_vc.mov'
        s['out'] = os.path.join(hrstate.dsub('reframed'), name)
    W, H, fps = probe(s['src'])
    t0, t1 = s['in'], s['out_t']
    ts, xs, ys, zs = path(s['keys'], t0, t1, fps, s.get('y', 50))
    cmds = []
    # Output aspect (9:16 default). The zoom-1.0 window is the largest window of that aspect inside the
    # source, so portrait phone clips, 4K and HD all work. Zoom is capped by how far the crop can shrink
    # before the upscale gets soft: crop height may go down to ~0.75 of the output height (1.15–2.0).
    aw, ah = (int(v) for v in s.get('aspect', '9:16').split(':'))
    OW, OH = OUT_SIZES.get(f'{aw}:{ah}', (1080, round(1080 * ah / aw / 2) * 2))
    ar = aw / ah
    base_h = H if W / H > ar else W / ar
    zmax = min(2.0, max(1.15, base_h / OH * 1.33))
    zs = np.clip(zs, 1.0, zmax)
    for i, (t, x, yv, z) in enumerate(zip(ts, xs, ys, zs)):
        ch = int(round(base_h / z / 2) * 2)
        cw = int(round(ch * ar / 2) * 2)
        cx = min(max(x / 100.0 * W - cw / 2, 0), W - cw)  # clamp: never show black edges
        cy = min(max(yv / 100.0 * H - ch / 2, 0), H - ch)
        rt = i / fps
        cmds.append(f'{rt:.4f} crop w {cw}, crop h {ch}, crop x {int(cx)}, crop y {int(cy)};')
    tmp = tempfile.mkdtemp()
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
    cmd = [FF, '-nostdin', '-v', 'error', '-y', '-ss', str(t0), '-t', str(t1 - t0), '-i', s['src'],
           '-vf', ','.join(vf), '-c:v', 'prores_ks', '-profile:v', '3', '-pix_fmt', 'yuv422p10le',
           '-c:a', 'pcm_s16le', s['out']]
    if fr:
        cmd[cmd.index('-c:a'):cmd.index('-c:a')] = ['-af', f"apad,atrim=duration={fr['t'] - t0 + fr['dur']:.4f}"]
    subprocess.run(cmd, check=True)
    print(s['out'], f'{len(ts)} frames @ {fps:.2f}')


if __name__ == '__main__':
    main(sys.argv[1])
