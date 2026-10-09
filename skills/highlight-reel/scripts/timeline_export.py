"""A deliverable's cut as an FCPXML 1.10 timeline that references the ORIGINAL footage — nothing is copied or
rendered. Used two ways:
  - Resolve path (hr-assemble): imported into the game's project (one timeline per aspect). Each play is the
    original clip trimmed to its window in the timeline, framed by Inspector keyframes (Pan, Tilt, Zoom)
    from vcam's operator path — the same keys an editor sets by hand, editable afterwards. The teaser's
    cliffhanger is a freeze-frame retime of the original. Measured on Resolve Studio 21.1: imports linked,
    keyframes animate on render, the freeze holds still.
  - Handoff (--handoff): the same file for another editor (Final Cut Pro, Premiere Pro, Resolve), written
    next to the delivered reel. Markers carry each play's beat; the lower-third text is a comment.

The colour stays camera-native (hr-grade / the editor grades in the NLE).

Usage: python3 timeline_export.py [DELIV_ID] [--aspect 9:16] [--handoff] [--out FILE.fcpxml]
  default output: <game>/tmp/timelines/<deliv>_<aspect>.fcpxml (scratch); prints one path per aspect

Import into Resolve with importSourceClips=True and a timeline name that doesn't exist yet. With
importSourceClips=False Resolve leaves every item offline, even for its own exported FCPXML of these files."""
import json, os, subprocess, sys
from fractions import Fraction
from urllib.parse import quote
from xml.sax.saxutils import escape
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hrstate, vcam

TL_FPS = Fraction(30000, 1001)
OUT_SIZES = vcam.OUT_SIZES


def rt(sec):
    """Seconds (Fraction) → FCPXML rational time string."""
    sec = Fraction(sec).limit_denominator(1000000)
    return f'{sec.numerator}/{sec.denominator}s' if sec else '0s'


def tl(sec):
    """Snap to the 29.97 timeline grid."""
    return Fraction(round(Fraction(sec).limit_denominator(100000) * TL_FPS)) / TL_FPS


def media_info(path):
    """{fps, frame (Fraction s), start (media start timecode in s), duration, width, height, audio}.
    Resolve places FCPXML source times against the file's own timecode, so asset/clip starts must carry it
    (a Canon R7 file starts at e.g. 08:01:12;48 — drop-frame — not at 0)."""
    o = json.loads(subprocess.run([hrstate.tool('ffprobe'), '-v', 'error', '-show_entries',
                                   'stream=codec_type,width,height,r_frame_rate:stream_tags=timecode:'
                                   'format=duration:format_tags=timecode', '-of', 'json', path],
                                  capture_output=True, text=True).stdout)
    v = next(s for s in o['streams'] if s['codec_type'] == 'video')
    fps = Fraction(v['r_frame_rate'])
    tc = (o.get('format', {}).get('tags') or {}).get('timecode') or next(
        (s.get('tags', {}).get('timecode') for s in o['streams'] if s.get('tags', {}).get('timecode')), None)
    return {'fps': fps, 'frame': 1 / fps, 'start': tc_seconds(tc, fps) if tc else Fraction(0),
            'duration': Fraction(o['format']['duration']).limit_denominator(1000000),
            'width': int(v['width']), 'height': int(v['height']),
            'audio': any(s['codec_type'] == 'audio' for s in o['streams'])}


def tc_seconds(tc, fps):
    """'HH:MM:SS:FF' (or ';' = drop-frame) at fps → seconds from 00:00:00:00, as Resolve counts them."""
    df = ';' in tc or '.' in tc
    h, m, s, f = (int(x) for x in tc.replace(';', ':').replace('.', ':').split(':'))
    nom = round(fps)
    frames = ((h * 60 + m) * 60 + s) * nom + f
    if df and fps.denominator == 1001:
        drop = round(nom / 15)                       # 2 per minute at 29.97, 4 at 59.94
        mins = h * 60 + m
        frames -= drop * (mins - mins // 10)
    return Fraction(frames) / fps


def items_for(d, asp):
    """Timeline items for one aspect: [{clip, role, beat, in, out, shotlist|None, freeze|None}]."""
    sel = d['select']; dr = d.get('direct') or {}
    shots = dr.get('shots') or dr.get('renders') or {}
    its = ([dict(sel['teaser'], role='teaser')] if sel.get('teaser') else []) + \
          [dict(s, role=s.get('role', 'play')) for s in sel['sequence']]
    out = []
    for it in its:
        sh = next((v for v in shots.values() if v.get('clip') == it['clip'] and v.get('aspect') == asp
                   and (v.get('role') == 'teaser') == (it['role'] == 'teaser')), None)
        if not sh and it['role'] == 'teaser':
            continue                                   # no directed teaser for this aspect
        out.append(dict(it, shotlist=sh and sh.get('shotlist')))
    return out


def key_at(keys, t):
    """The (linear) keyframe value at source time t, as one key — what the freeze frame holds."""
    if not keys:
        return None
    if t <= keys[0]['t'] or len(keys) == 1:
        return dict(keys[0], t=t)
    if t >= keys[-1]['t']:
        return dict(keys[-1], t=t)
    a, b = next((keys[i], keys[i + 1]) for i in range(len(keys) - 1) if keys[i]['t'] <= t <= keys[i + 1]['t'])
    u = (t - a['t']) / (b['t'] - a['t']) if b['t'] > a['t'] else 0
    return {'t': t, **{c: a[c] + (b[c] - a[c]) * u for c in ('pan', 'tilt', 'zoom')}}


def transform_xml(keys, asset_start, TH):
    """Inspector keyframes → <adjust-transform>. Position is in % of the timeline HEIGHT on both axes
    (Resolve wrote Pan 500 px on a 1920-high timeline as 26.0417); scale is relative to "fit"."""
    if not keys:
        return ''
    pos = lambda k: f"{k['pan'] / TH * 100:.4f} {k['tilt'] / TH * 100:.4f}"
    sc = lambda k: f"{k['zoom']:.4f} {k['zoom']:.4f}"
    if len(keys) == 1:
        return f'<adjust-transform anchor="0 0" position="{pos(keys[0])}" scale="{sc(keys[0])}"/>'
    kt = lambda k: rt(asset_start + Fraction(k['t']).limit_denominator(1000000))
    zs = {k['zoom'] for k in keys}
    pk = ''.join(f'<keyframe time="{kt(k)}" value="{pos(k)}"/>' for k in keys)
    sx = (f'<param name="scale"><keyframeAnimation>'
          + ''.join(f'<keyframe time="{kt(k)}" value="{sc(k)}"/>' for k in keys)
          + '</keyframeAnimation></param>') if len(zs) > 1 else ''
    return (f'<adjust-transform anchor="0 0" position="{pos(keys[0])}" scale="{sc(keys[0])}">'
            f'<param name="position"><keyframeAnimation>{pk}</keyframeAnimation></param>{sx}</adjust-transform>')


def build(did=None, asp='9:16', name=None):
    """FCPXML for one aspect of the deliverable; returns (xml, summary)."""
    d = hrstate.load('deliv', did); TW, TH = OUT_SIZES[asp]
    name = name or f"{d['id']}_{asp.replace(':', 'x')}"
    res = [f'<format id="tl" frameDuration="1001/30000s" width="{TW}" height="{TH}"/>']
    assets, spine, summary, offset = {}, [], [], Fraction(0)

    def asset(path):
        if path not in assets:
            m = media_info(path); aid = f'a{len(assets)}'; fid = f'f{len(assets)}'
            res.append(f'<format id="{fid}" frameDuration="{rt(m["frame"])}" width="{m["width"]}" height="{m["height"]}"/>')
            res.append(f'<asset id="{aid}" name="{escape(os.path.basename(path))}" start="{rt(m["start"])}" '
                       f'duration="{rt(m["duration"])}" hasVideo="1" hasAudio="{int(m["audio"])}" format="{fid}">'
                       f'<media-rep kind="original-media" src="file://{quote(path)}"/></asset>')
            assets[path] = (aid, fid, m)
        return assets[path]

    for it in items_for(d, asp):
        c = hrstate.get(f"media.clips.{it['clip']}"); path = c['path']
        aid, fid, m = asset(path)
        snap = lambda t: Fraction(round(Fraction(t).limit_denominator(100000) / m['frame'])) * m['frame']
        keys, freeze, sl = [], None, it.get('shotlist')
        if sl:
            pl = vcam.plan(sl); keys = vcam.resolve_keys(pl, (TW, TH)); freeze = pl['spec'].get('freeze')
        elif abs(m['width'] / m['height'] - TW / TH) > 0.05:
            sys.exit(f"timeline_export: {it['clip']} ({it['role']}) has no {asp} shot list — run hr-direct")
        t_in = snap(it['in']); t_out = snap(freeze['t'] if freeze else it['out'])
        dur = tl(t_out - t_in)
        beat = escape(it.get('beat') or it['role'])
        spine.append(f'<asset-clip ref="{aid}" name="{escape(it["clip"])}" offset="{rt(offset)}" '
                     f'start="{rt(m["start"] + t_in)}" duration="{rt(dur)}" format="{fid}" tcFormat="NDF">'
                     f'<marker start="{rt(m["start"] + t_in)}" duration="1001/30000s" value="{beat}"/>'
                     f'{transform_xml(keys, m["start"], TH)}</asset-clip>')
        summary.append({'clip': it['clip'], 'role': it['role'], 'record_s': float(offset), 'dur_s': float(dur),
                        'src_in_s': float(t_in), 'keys': len(keys)})
        offset += dur
        if freeze:   # hold the source frame at freeze t (a retime of the original), game sound muted
            fdur = tl(Fraction(freeze['dur']).limit_denominator(1000))
            ft = m['start'] + t_out
            last = key_at(keys, float(t_out))
            spine.append(f'<asset-clip ref="{aid}" name="{escape(it["clip"])} freeze" offset="{rt(offset)}" '
                         f'start="{rt(ft)}" duration="{rt(fdur)}" format="{fid}" tcFormat="NDF">'
                         f'<timeMap><timept time="{rt(ft)}" value="{rt(ft)}" interp="linear"/>'
                         f'<timept time="{rt(ft + fdur)}" value="{rt(ft)}" interp="linear"/></timeMap>'
                         f'<adjust-volume amount="-96dB"/>{transform_xml([last] if last else [], m["start"], TH)}'
                         f'</asset-clip>')
            summary.append({'clip': it['clip'], 'role': 'freeze', 'record_s': float(offset), 'dur_s': float(fdur),
                            'src_in_s': float(t_out), 'keys': 1 if last else 0})
            offset += fdur
    lt = ''
    try:
        import finish
        lt = ' / '.join(x for x in finish.lower_third_text(d) if x)
    except Exception:
        pass
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n<fcpxml version="1.10">'
           f'<resources>{"".join(res)}</resources>'
           f'<library><event name="{escape(name)}"><project name="{escape(name)}">'
           f'<sequence format="tl" duration="{rt(offset)}" tcStart="0s" tcFormat="NDF"><spine>{"".join(spine)}</spine>'
           f'</sequence></project></event></library><!-- lower third: {escape(lt)} --></fcpxml>\n')
    return xml, {'timeline': name, 'aspect': asp, 'total_s': float(offset), 'items': summary}


if __name__ == '__main__':
    a = sys.argv[1:]
    opt = lambda k: a[a.index(k) + 1] if k in a else None
    out, only = opt('--out'), opt('--aspect')
    did = next((x for x in a if not x.startswith('--') and x not in (out, only)), None)
    d = hrstate.load('deliv', did)
    for asp in [only] if only else d.get('aspects', ['16:9']):
        xml, info = build(did, asp)
        if out:
            path = out
        elif '--handoff' in a:
            path = os.path.join(hrstate.config('output_folder'), 'handoff', f"{info['timeline']}.fcpxml")
        else:
            path = os.path.join(hrstate.sub('tmp'), 'timelines', f"{info['timeline']}.fcpxml")
        os.makedirs(os.path.dirname(path), exist_ok=True); open(path, 'w').write(xml)
        info['fcpxml'] = path
        hrstate.set_(f"timelines.{asp.replace(':', 'x')}", info, scope='deliv', sid=did)
        print(path, json.dumps({k: info[k] for k in ('timeline', 'total_s')}),
              ' '.join(f"{i['clip']}:{i['role']}:{i['keys']}k" for i in info['items']))
