"""Virtual camera: render a 9:16 reframe of a 16:9 clip from a shot list.

Usage: python3 vcam.py shotlist.json

shotlist.json:
{
  "src": "R7__1630",                        # clip name (looked up in reel.json) or a path
  "out": "/path/R7__1630_vc.mov",           # optional; default <workspace>/reframed/<clip>_vc.mov
  "in": 2.6, "out_t": 10.8,                # source seconds
  "keys": [                                 # x: 0-100 across source width (vgrid ruler)
    {"t": 2.6, "x": 33, "zoom": 1.35, "subject": "player", "event": "possession"},
    {"t": 4.2, "x": 62, "zoom": 1.25, "subject": "ball", "event": "shot", "move": "fast"},
    ...
  ],
  "y": 55,                                  # optional vertical centre 0-100 (default 50)
  "freeze": {"t": 4.5, "dur": 1.5},         # optional: hold this source time (cold-open teaser)
  "whip_out": true                          # optional: horizontal blur ramp on the last 0.2s
}
zoom 1.0 = full-height 9:16 window; 1.3 = 30% tighter. move "fast" = whip to that key
(shot/pass), default "smooth" = eased follow.
Output: ProRes 422 HQ 10-bit, Log preserved (no colour change), audio PCM.
"""
import json, sys, subprocess, os, tempfile
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hrstate

FF = '/opt/homebrew/bin/ffmpeg'; FP = '/opt/homebrew/bin/ffprobe'


def probe(src):
    o = subprocess.run([FP, '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                        'stream=width,height,r_frame_rate', '-of', 'csv=p=0', src],
                       capture_output=True, text=True).stdout.strip().split(',')
    n, d = o[2].split('/')
    return int(o[0]), int(o[1]), float(n) / float(d)


def path(keys, t0, t1, fps):
    """Per-frame (x, zoom). Smooth keys ease with smoothstep; 'fast' keys get a short whip."""
    keys = sorted(keys, key=lambda k: k['t'])
    ts = np.arange(t0, t1, 1.0 / fps)
    xs, zs = np.empty_like(ts), np.empty_like(ts)
    for i, t in enumerate(ts):
        if t <= keys[0]['t']:
            xs[i], zs[i] = keys[0]['x'], keys[0].get('zoom', 1.0); continue
        if t >= keys[-1]['t']:
            xs[i], zs[i] = keys[-1]['x'], keys[-1].get('zoom', 1.0); continue
        j = max(k for k in range(len(keys)) if keys[k]['t'] <= t)
        a, b = keys[j], keys[j + 1]
        u = (t - a['t']) / (b['t'] - a['t'])
        if b.get('move') == 'fast':          # reach the new subject in <=0.25s, then track
            span = b['t'] - a['t']; u = min(1.0, u * span / min(span, 0.25))
        u = u * u * (3 - 2 * u)              # smoothstep ease in/out
        xs[i] = a['x'] + (b['x'] - a['x']) * u
        zs[i] = a.get('zoom', 1.0) + (b.get('zoom', 1.0) - a.get('zoom', 1.0)) * u
    # light extra smoothing (0.2s window) to kill keyframe kinks, but not across fast moves
    k = max(1, int(fps * 0.2)) | 1
    pad = k // 2
    xs = np.convolve(np.pad(xs, pad, mode='edge'), np.ones(k) / k, mode='valid')
    return ts, xs, zs


def main(spec_path):
    s = json.load(open(spec_path))
    if not os.path.exists(s['src']):
        s['src'] = hrstate.get(f"media.clips.{s['src']}.path") or sys.exit(f"unknown clip {s['src']}")
    if not s.get('out'):
        s['out'] = os.path.join(hrstate.sub('reframed'), os.path.splitext(os.path.basename(s['src']))[0] + '_vc.mov')
    W, H, fps = probe(s['src'])
    t0, t1 = s['in'], s['out_t']
    ts, xs, zs = path(s['keys'], t0, t1, fps)
    yc = s.get('y', 50) / 100.0
    cmds = []
    for i, (t, x, z) in enumerate(zip(ts, xs, zs)):
        ch = int(round(H / max(z, 1.0) / 2) * 2)          # crop height (even)
        cw = int(round(ch * 9 / 16 / 2) * 2)              # 9:16 width (even)
        cx = min(max(x / 100.0 * W - cw / 2, 0), W - cw)  # clamp: never show black edges
        cy = min(max(yc * H - ch / 2, 0), H - ch)
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
          f'scale=1080:1920:flags=lanczos:in_range={in_rng}:out_range=tv', 'setsar=1']
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
