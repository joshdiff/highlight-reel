"""Hand a deliverable's cut to another editor: FCPXML 1.9 (Final Cut Pro; Premiere Pro and DaVinci Resolve
import it too). One project per aspect: the clips in select order — the vcam reframes where they exist,
otherwise the original media trimmed to the window — with a marker per play (its beat) and the lower-third
text as a note. The colour stays camera-native, so the editor grades in their NLE.

Usage: python3 timeline_export.py [DELIV_ID] [--out FILE.fcpxml]   default <deliverable>/handoff/<id>.fcpxml"""
import json, os, subprocess, sys
from fractions import Fraction
from urllib.parse import quote
from xml.sax.saxutils import escape
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hrstate

FPS = Fraction(30000, 1001)
OUT_SIZES = {'9:16': (1080, 1920), '1:1': (1080, 1080), '4:5': (1080, 1350), '16:9': (1920, 1080)}


def t(sec):
    """Seconds → FCPXML rational time on the 29.97 frame grid ("1001/30000s" units)."""
    frames = round(Fraction(sec).limit_denominator(100000) * FPS)
    return f'{frames * 1001}/30000s' if frames else '0s'


def probe(p):
    o = json.loads(subprocess.run([hrstate.tool('ffprobe'), '-v', 'error', '-show_entries',
                                   'stream=codec_type,width,height:format=duration', '-of', 'json', p],
                                  capture_output=True, text=True).stdout)
    v = next(s for s in o['streams'] if s['codec_type'] == 'video')
    return v['width'], v['height'], float(o['format']['duration']), any(s['codec_type'] == 'audio' for s in o['streams'])


def build(did=None):
    d = hrstate.load('deliv', did); sel = d['select']; renders = (d.get('direct') or {}).get('renders', {})
    items = ([dict(sel['teaser'], role='teaser')] if sel.get('teaser') else []) + [dict(s) for s in sel['sequence']]
    resources, projects, assets = [], [], {}
    for ai, asp in enumerate(d.get('aspects', ['16:9'])):
        W, H = OUT_SIZES[asp]; fmt = f'r_fmt{ai}'
        resources.append(f'<format id="{fmt}" frameDuration="1001/30000s" width="{W}" height="{H}"/>')
        spine, offset = [], 0.0
        for it in items:
            r = next((v for v in renders.values() if v.get('clip') == it['clip'] and v.get('aspect') == asp
                      and (v.get('role') == 'teaser') == (it.get('role') == 'teaser')), None)
            if r:
                path, start = r['out'], 0.0; dur = probe(path)[2]
            elif it.get('role') == 'teaser':
                continue
            else:
                path = hrstate.get(f"media.clips.{it['clip']}.path"); start = it['in']; dur = it['out'] - it['in']
            if path not in assets:
                w, h, full, has_a = probe(path); aid = f'r_a{len(assets)}'
                assets[path] = aid
                resources.append(f'<asset id="{aid}" name="{escape(os.path.basename(path))}" start="0s" duration="{t(full)}" '
                                 f'hasVideo="1" hasAudio="{int(has_a)}" format="{fmt}">'
                                 f'<media-rep kind="original-media" src="file://{quote(path)}"/></asset>')
            beat = escape(it.get('beat') or it.get('role') or '')
            spine.append(f'<asset-clip ref="{assets[path]}" name="{escape(it["clip"])}" offset="{t(offset)}" '
                         f'start="{t(start)}" duration="{t(dur)}" format="{fmt}">'
                         f'<marker start="{t(start)}" duration="1001/30000s" value="{beat}"/></asset-clip>')
            offset += dur
        projects.append(f'<project name="{escape(d["id"])} {asp}"><sequence format="{fmt}" duration="{t(offset)}" '
                        f'tcStart="0s" tcFormat="NDF"><spine>{"".join(spine)}</spine></sequence></project>')
    lt = ''
    try:
        import finish
        lt = ' / '.join(x for x in finish.lower_third_text(d) if x)
    except Exception:
        pass
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n<fcpxml version="1.9">'
            f'<resources>{"".join(resources)}</resources>'
            f'<library><event name="{escape(hrstate.get("id") or "highlight-reel")}">'
            f'{"".join(projects)}</event></library>'
            f'<!-- lower third: {escape(lt)} --></fcpxml>\n')


if __name__ == '__main__':
    a = sys.argv[1:]
    out = a[a.index('--out') + 1] if '--out' in a else None
    did = next((x for x in a if not x.startswith('--') and x != out), None)
    xml = build(did)
    out = out or os.path.join(hrstate.deliv_dir(did), 'handoff', f"{hrstate.load('deliv', did)['id']}.fcpxml")
    os.makedirs(os.path.dirname(out), exist_ok=True); open(out, 'w').write(xml)
    hrstate.set_('handoff', {'fcpxml': out}, scope='deliv', sid=did)
    print(out)
