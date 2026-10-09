"""ffmpeg finishing path — no NLE needed. For the current deliverable, per aspect:
  1. each play (teaser, then select.sequence): the vcam render for that aspect, or the original trimmed
     to its window when the aspect matches the source (16:9 from 16:9)
  2. colour per source encoding: camera profile `lut` (official) or the built-in luts.py transform,
     then the CDL (deliv grade.cdl.<encoding> → brand grade.cdl → default), then the brand creative LUT
  3. normalised to the output size, 29.97 CFR, ProRes intermediates; brand intro/outro bumpers
  4. concat → lower third (PNG from the brand) over the teaser, watermark, music bed ducked under the
     game audio, loudness to the brand target → H.264 MP4
  5. gradecheck on the result
Output: <deliverable>/finished/<aspect>.mp4 and deliv.finish {files, stats, colour}. hr-export names and
delivers them.

Usage: python3 finish.py [--aspect 9:16] [--music none|auto|FILE] [--keep]"""
import hashlib, json, os, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hrstate, library, luts, cameras, look

FF = hrstate.tool('ffmpeg'); FP = hrstate.tool('ffprobe')
OUT_SIZES = {'9:16': (1080, 1920), '1:1': (1080, 1080), '4:5': (1080, 1350), '16:9': (1920, 1080)}
RATE = '30000/1001'


def run(args):
    subprocess.run([FF, '-nostdin', '-v', 'error', '-y'] + args, check=True)


def probe(path):
    o = json.loads(subprocess.run([FP, '-v', 'error', '-show_entries', 'stream=codec_type,width,height,color_range:format=duration',
                                   '-of', 'json', path], capture_output=True, text=True).stdout)
    v = next((s for s in o['streams'] if s['codec_type'] == 'video'), {})
    return {'w': v.get('width'), 'h': v.get('height'), 'range': v.get('color_range'),
            'audio': any(s['codec_type'] == 'audio' for s in o['streams']), 'dur': float(o['format']['duration'])}


def hex_rgb(h, a=255):
    h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (a,)


# ---------- colour ----------
def colour_chain(enc, camera_id, cdl, creative, corr=None):
    """corr: look.py correction for this play (stops, r, b, sat) — applied in the built-in LUT's scene-linear
    stage; with an official camera LUT it is approximated after the LUT as display-space gains."""
    f = []; corr = corr or look.ZERO
    prof = cameras.profiles().get(camera_id or '', {})
    lut = prof.get('lut') or (luts.cube_path(enc, **look.lut_args(corr)) if enc in luts.ENC else None)
    if lut:
        f.append(f"lut3d=file='{lut}':interp=tetrahedral")
    if prof.get('lut') and corr != look.ZERO:
        kr, kg, kb = (2 ** ((corr['stops'] + corr.get(c, 0)) / 2.4) for c in ('r', 'g', 'b'))
        f.append(f'colorchannelmixer=rr={kr:.4f}:gg={kg:.4f}:bb={kb:.4f}')
    cdl = dict(cdl, sat=cdl.get('sat', 1.0) * corr.get('sat', 1.0))
    s, o, p = cdl.get('slope', 1.0), cdl.get('offset', 0.0), cdl.get('power', 1.0)
    if (s, o, p) != (1.0, 0.0, 1.0):
        e = f"clip(pow(clip(val/maxval*{s}+{o}\\,0\\,1)\\,{p})*maxval\\,0\\,maxval)"
        f.append(f"lutrgb=r='{e}':g='{e}':b='{e}'")
    sat = cdl.get('sat', 1.0)
    if sat != 1.0:
        k = 1 - sat; R, G, B = 0.2126 * k, 0.7152 * k, 0.0722 * k
        f.append(f'colorchannelmixer=rr={R + sat:.4f}:rg={G:.4f}:rb={B:.4f}:gr={R:.4f}:gg={G + sat:.4f}:gb={B:.4f}'
                 f':br={R:.4f}:bg={G:.4f}:bb={B + sat:.4f}')
    if creative:
        f.append(f"lut3d=file='{creative}'")
    return f


def cdl_for(enc, deliv, brand):
    return (deliv.get('grade', {}).get('cdl', {}) or {}).get(enc) or brand['grade']['cdl']


def solve_look(p, cdl, work, passes=5):
    """Per-play correction to the neutral-standard target (look.py): render 3 frames through the colour
    chain, measure, re-solve; stop when converged. Cached in deliv.grade.look.<file>."""
    key = os.path.basename(p['file']) + (f"@{p['in']}" if p.get('in') is not None else '')
    cache = hrstate.get('grade.look', scope='deliv') or {}
    if key in cache:
        return cache[key]['correction']
    dur = float(subprocess.run([FP, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p['file']],
                               capture_output=True, text=True).stdout.strip())
    a, b = (p['in'], p['out']) if p.get('in') is not None else (0.0, dur)
    corr, res, hist = dict(look.ZERO), None, []
    rng = 'full' if p.get('range') == 'pc' else 'tv'
    for k in range(passes):
        chain = ','.join([f'scale=540:-2:in_range={rng}:out_range=tv', 'format=rgb48le'] +
                         colour_chain(p['enc'], p['camera'], cdl, None, corr))
        frames = []
        for j, t in enumerate((a + (b - a) * f for f in (0.25, 0.5, 0.75))):
            out = os.path.join(work, f'look_{k}_{j}.png')
            subprocess.run([FF, '-nostdin', '-v', 'error', '-y', '-ss', f'{t:.3f}', '-i', p['file'], '-frames:v', '1',
                            '-vf', chain, out], check=True)
            frames.append(out)
        res = look.solve(frames, corr, history=hist); res.pop('frames'); hist.append(res['point'])
        if res['converged']:
            break
        corr = res['correction']
    cache[key] = {'correction': corr, 'basis': res['basis'], 'measured_luma': res['measured_luma'],
                  'target_luma': res['target_luma'], 'converged': res['converged']}
    hrstate.set_('grade.look', cache, scope='deliv')
    return corr


# ---------- pieces ----------
def plays(deliv, aspect):
    sel = deliv['select']; renders = (deliv.get('direct') or {}).get('renders', {})
    items = ([dict(sel['teaser'], role='teaser')] if sel.get('teaser') else []) + \
            [dict(s, role=s.get('role', 'play')) for s in sel['sequence']]
    out = []
    for it in items:
        r = next((v for v in renders.values() if v.get('clip') == it['clip'] and v.get('aspect') == aspect
                  and (v.get('role') == 'teaser') == (it['role'] == 'teaser')), None)
        c = hrstate.get(f"media.clips.{it['clip']}")
        if r:
            out.append({'file': r['out'], 'in': None, 'out': None, 'clip': it['clip'], 'role': it['role'],
                        'enc': c.get('encoding'), 'camera': c.get('camera'), 'range': 'tv'})
        else:
            aw, ah = (int(v) for v in aspect.split(':'))
            if abs(c['width'] / c['height'] - aw / ah) > 0.05:
                sys.exit(f"finish: no {aspect} render for {it['clip']} ({it['role']}) — run hr-direct for this aspect")
            if it['role'] == 'teaser':
                continue          # a 16:9 deliverable has no freeze teaser unless directed
            out.append({'file': c['path'], 'in': it['in'], 'out': it['out'], 'clip': it['clip'], 'role': it['role'],
                        'enc': c.get('encoding'), 'camera': c.get('camera'),
                        'range': 'pc' if c.get('range') == 'pc' else 'tv'})
    return out


def intermediate(p, i, OW, OH, deliv, brand, work, kind='play'):
    dst = os.path.join(work, f'{i:03d}_{kind}.mov')
    vf = []
    rng = 'full' if p.get('range') == 'pc' else 'tv'
    vf.append(f'scale={OW}:{OH}:force_original_aspect_ratio=increase:flags=lanczos:in_range={rng}:out_range=tv,crop={OW}:{OH}')
    vf.append('format=rgb48le')
    if kind == 'play':
        cdl = cdl_for(p['enc'], deliv, brand)
        corr = solve_look(p, cdl, work)
        vf += colour_chain(p['enc'], p['camera'], cdl, brand['grade'].get('creative_lut'), corr)
    vf += [f'fps={RATE}', 'format=yuv422p10le', 'setsar=1']
    args = []
    if p.get('in') is not None:
        args += ['-ss', f"{p['in']:.3f}", '-t', f"{p['out'] - p['in']:.3f}"]
    args += ['-i', p['file']]
    has_a = probe(p['file'])['audio']
    if not has_a:
        args += ['-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo']
    args += ['-vf', ','.join(vf), '-map', '0:v:0', '-map', '0:a:0' if has_a else '1:a:0',
             '-c:v', 'prores_ks', '-profile:v', '3', '-c:a', 'pcm_s16le', '-ar', '48000', '-ac', '2', '-shortest',
             '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', dst]
    run(args)
    return dst


# ---------- graphics ----------
def _font(brand, size, bold=False):
    from PIL import ImageFont
    for f in ([brand['font']] if brand.get('font') else []) + \
             (['/System/Library/Fonts/Supplemental/Arial Bold.ttf'] if bold else []) + \
             ['/System/Library/Fonts/Helvetica.ttc', '/System/Library/Fonts/Supplemental/Arial.ttf']:
        try:
            return ImageFont.truetype(f, size)
        except (OSError, TypeError):
            continue
    return ImageFont.load_default()


def lower_third_png(lines, brand, OW, OH, out):
    from PIL import Image, ImageDraw
    lt = brand['lower_third']; c = brand['colors']
    h1 = int(OH * lt.get('size', 0.03)); h2 = int(h1 * 0.62)
    f1, f2 = _font(brand, h1, True), _font(brand, h2)
    im = Image.new('RGBA', (OW, OH), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    w1 = d.textlength(lines[0] or '', font=f1); w2 = d.textlength(lines[1] or '', font=f2) if lines[1] else 0
    logo = None
    if lt.get('show_logo') and brand.get('logo') and os.path.exists(brand['logo']):
        logo = Image.open(brand['logo']).convert('RGBA'); s = (h1 + h2 + h1 * 0.4) / logo.height
        logo = logo.resize((max(1, int(logo.width * s)), max(1, int(logo.height * s))))
    pad = int(h1 * 0.45); lw = (logo.width + pad) if logo else 0
    bw = int(max(w1, w2) + 2 * pad + lw); bh = int(h1 + (h2 * 1.25 if lines[1] else 0) + 2 * pad)
    x0 = (OW - bw) // 2; y0 = int(OH * lt.get('position_y', 0.78) - bh / 2)
    if lt.get('style', 'bar') == 'bar':
        d.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], radius=int(pad * 0.6), fill=hex_rgb(c['primary'], 215))
        d.rectangle([x0, y0 + bh - max(3, pad // 4), x0 + bw, y0 + bh], fill=hex_rgb(c['secondary'], 255))
    if logo:
        im.alpha_composite(logo, (x0 + pad, y0 + (bh - logo.height) // 2))
    tx = x0 + pad + lw
    d.text((tx, y0 + pad - int(h1 * 0.1)), lines[0] or '', font=f1, fill=hex_rgb(c['text']))
    if lines[1]:
        d.text((tx, y0 + pad + int(h1 * 1.1)), lines[1], font=f2, fill=hex_rgb(c['text'], 230))
    im.save(out); return out


def watermark_png(brand, OW, OH, out):
    from PIL import Image
    wm = brand.get('watermark')
    if not wm or not wm.get('file') or not os.path.exists(wm['file']):
        return None
    im = Image.open(wm['file']).convert('RGBA'); s = OW * wm.get('scale', 0.12) / im.width
    im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))))
    a = im.getchannel('A').point(lambda v: int(v * wm.get('opacity', 0.7))); im.putalpha(a)
    canvas = Image.new('RGBA', (OW, OH), (0, 0, 0, 0)); m = int(OW * 0.035)
    pos = wm.get('position', 'tr')
    x = m if pos[1] == 'l' else OW - im.width - m; y = m if pos[0] == 't' else OH - im.height - m
    canvas.alpha_composite(im, (x, y)); canvas.save(out); return out


def lower_third_text(deliv):
    t = hrstate._read(os.path.join(hrstate.game_dir(), 'targets', deliv['target'], 'find.json'), {})
    g = hrstate.load('game'); side = t.get('side', 'home'); team = g['teams'][side]
    other = g['teams']['away' if side == 'home' else 'home']['name']
    if t.get('player_id'):
        import hrprofile
        p = hrprofile.load('player', t['player_id']); lt = p.get('lower_third') or {}
        m = hrprofile.membership(p, team.get('team_id')) or {}
        l2 = lt.get('line2') or (f"{team['name']} - c/o {p['grad_year']}" if p.get('grad_year')
                                 else f"#{m.get('number', '')} | {team['name']}")
        return [lt.get('line1') or p['name'], l2]
    return [team['name'], f'vs {other}']


def pick_music(deliv, brand, mode):
    if mode == 'none':
        return None
    if mode not in ('auto', None) and os.path.exists(mode):
        return mode
    if deliv.get('music') and deliv['music'] not in ('auto', 'none') and os.path.exists(deliv['music']):
        return deliv['music']
    if deliv.get('music') == 'none' or (mode in ('auto', None) and deliv['type'] in ('recruiting_tape', 'scoring_reel', 'goals_reel')):
        return None
    folder = brand['music'].get('folder')
    if not folder or not os.path.isdir(folder):
        return None
    tracks = sorted(f for f in os.listdir(folder) if f.lower().endswith(('.mp3', '.m4a', '.wav', '.aac', '.aif', '.aiff', '.flac')))
    if not tracks:
        return None
    return os.path.join(folder, tracks[int(hashlib.md5(deliv['id'].encode()).hexdigest(), 16) % len(tracks)])


# ---------- assemble ----------
def finish_aspect(deliv, aspect, brand, music_mode, keep):
    OW, OH = OUT_SIZES[aspect]
    work = os.path.join(hrstate.deliv_dir(), 'finish', aspect.replace(':', 'x')); shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    parts, i = [], 0
    if brand.get('intro') and os.path.exists(brand['intro']):
        parts.append(intermediate({'file': brand['intro']}, i, OW, OH, deliv, brand, work, 'intro')); i += 1
    intro_len = probe(parts[0])['dur'] if parts else 0.0
    teaser_len = 0.0
    for p in plays(deliv, aspect):
        f = intermediate(p, i, OW, OH, deliv, brand, work); i += 1; parts.append(f)
        if p['role'] == 'teaser':
            teaser_len = probe(f)['dur']
    if brand.get('outro') and os.path.exists(brand['outro']):
        parts.append(intermediate({'file': brand['outro']}, i, OW, OH, deliv, brand, work, 'outro')); i += 1
    lst = os.path.join(work, 'list.txt')
    open(lst, 'w').write(''.join(f"file '{p}'\n" for p in parts))
    cat = os.path.join(work, 'concat.mov'); run(['-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', cat])
    total = probe(cat)['dur']

    inputs = ['-i', cat]; vchain = '[0:v]'; fc = []; n = 1
    lt_png = lower_third_png(lower_third_text(deliv), brand, OW, OH, os.path.join(work, 'lt.png'))
    lt_end = intro_len + (teaser_len or min(3.0, total))
    inputs += ['-loop', '1', '-t', f'{total:.3f}', '-i', lt_png]
    fc.append(f"[{n}:v]format=rgba,fade=t=in:st={intro_len:.3f}:d=0.3:alpha=1,fade=t=out:st={max(intro_len, lt_end - 0.3):.3f}:d=0.3:alpha=1[lt]")
    fc.append(f"{vchain}[lt]overlay=0:0:enable='between(t,{intro_len:.3f},{lt_end:.3f})'[v1]"); vchain = '[v1]'; n += 1
    wm = watermark_png(brand, OW, OH, os.path.join(work, 'wm.png'))
    if wm:
        inputs += ['-loop', '1', '-t', f'{total:.3f}', '-i', wm]
        outro_start = total - (probe(parts[-1])['dur'] if brand.get('outro') and os.path.exists(brand['outro']) else 0)
        fc.append(f"{vchain}[{n}:v]overlay=0:0:enable='between(t,{intro_len:.3f},{outro_start:.3f})'[v2]"); vchain = '[v2]'; n += 1
    fc.append(f'{vchain}format=yuv420p[vout]')

    social = aspect != '16:9'
    lufs = brand['loudness']['social' if social else 'landscape']
    music = pick_music(deliv, brand, music_mode)
    if music:
        inputs += ['-stream_loop', '-1', '-i', music]
        vol = brand['music'].get('volume_db', -16)
        fc.append(f"[{n}:a]atrim=0:{total:.3f},asetpts=PTS-STARTPTS,volume={vol}dB,afade=t=out:st={max(0, total - 2):.3f}:d=2[mus]")
        if brand['music'].get('duck', True):     # music dips whenever the game audio is loud
            fc.append('[0:a]asplit=2[game][key]')
            fc.append('[mus][key]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[bed]')
            fc.append(f'[game][bed]amix=inputs=2:duration=first:normalize=0,loudnorm=I={lufs}:TP=-1:LRA=11[aout]')
        else:
            fc.append(f'[0:a][mus]amix=inputs=2:duration=first:normalize=0,loudnorm=I={lufs}:TP=-1:LRA=11[aout]')
    else:
        fc.append(f'[0:a]loudnorm=I={lufs}:TP=-1:LRA=11[aout]')
    out = os.path.join(hrstate.deliv_dir(), 'finished', f"{aspect.replace(':', 'x')}.mp4"); os.makedirs(os.path.dirname(out), exist_ok=True)
    kbps = 14000 if social else (25000 if deliv['type'] == 'recruiting_tape' else 20000)
    run(inputs + ['-filter_complex', ';'.join(fc), '-map', '[vout]', '-map', '[aout]',
                  '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-maxrate', f'{kbps}k', '-bufsize', f'{kbps * 2}k',
                  '-profile:v', 'high', '-pix_fmt', 'yuv420p', '-r', RATE,
                  '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709',
                  '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-movflags', '+faststart', '-t', f'{total:.3f}', out])
    if not keep:
        shutil.rmtree(work, ignore_errors=True)
    return out, {'music': music, 'lower_third': lower_third_text(deliv), 'duration': round(total, 2), 'lufs': lufs}


def main(a):
    deliv = hrstate.load('deliv')
    if not deliv.get('select'):
        sys.exit('finish: select not done for this deliverable')
    brand = library.brand(deliv.get('brand_id'))
    aspects = [a[a.index('--aspect') + 1]] if '--aspect' in a else deliv.get('aspects', ['9:16'])
    music = a[a.index('--music') + 1] if '--music' in a else None
    files, info, stats = {}, {}, {}
    import gradecheck
    from PIL import Image
    for asp in aspects:
        out, inf = finish_aspect(deliv, asp, brand, music, '--keep' in a)
        files[asp] = out; info[asp] = inf
        st = {name: gradecheck.stats(Image.open(p), p) for name, p in gradecheck.sample_video(out, 8)}
        stats[asp] = st; bad = [k for k, v in st.items() if not v['ok']]
        print(f"{asp}: {out}  {inf['duration']}s  music={'yes' if inf['music'] else 'no'}  "
              f"grade {len(st) - len(bad)}/{len(st)} frames in range"
              + ('; out: ' + ', '.join(f"{k} luma {st[k]['luma']} vivid {st[k]['vivid_pct']}% clip {st[k]['clip_pct']}%" for k in bad[:3]) if bad else ''))
    hrstate.set_('finish', {'files': files, 'info': info, 'stats': stats}, scope='deliv')


if __name__ == '__main__':
    main(sys.argv[1:])
