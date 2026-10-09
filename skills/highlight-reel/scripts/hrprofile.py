"""Library of players and teams — profiles that get better with every game processed.

Local only ($HR_HOME/library, default ~/.hr_work/library — never in the repo):
  players/<id>/profile.json + refs/*.jpg      teams/<id>.json
Schemas: see examples/ in the repo.

How a player profile learns (after hr-find, again after hr-export):
  learn PLAYER --game GAME --target TARGET  reads that target's find.json and, idempotently per game:
    - saves reference crops of CONFIRMED sightings (refs/, tagged with kit, encoding, cues)
    - id_stats: how often each cue (number, hair, boots, build, ...) confirmed her, and what misled
    - observations: dated appearance notes; fills empty appearance fields, flags conflicts (new number,
      haircut) in `flags`
    - style: tallies of her events (goal, take-on, kill, 3pt …), foot/hand, positions, areas
    - games: date, event, team, confirmed clips, best clips, outputs
  feedback PLAYER keep|drop "text" [--deliv D] [--clip C]   the client's verdicts; hr-select applies them

CLI (python3 hrprofile.py ...):
  list [players|teams] [--recent]       one line each; --recent sorts players by last game (setup pick-lists)
  show player|team ID                   full JSON
  brief PLAYER_ID [TEAM_ID]             what hr-find works from: number on that team, kit, look, cue ranking,
                                        decoys, refs, style, preferences, flags
  new player ID --name "Full Name" [--team TEAM_ID --number N] [--grad YEAR] [--sport S] [--client C]
  new team ID --name "Team Name" [--sport S] [--folder "media folder"] [--color "shirt"] [--client C]
  set|merge player|team ID KEY VALUE|FILE   dotted key (VALUE parsed as JSON, else a string)
  note player|team ID "text"            append a dated lesson
  ref add PLAYER --src FILE --t SEC --box x0,y0,x1,y1 [--kit K --enc E --cues number,hair --game G --clip C]
  refsheet PLAYER [--out F.jpg] [--kit K] [--n 24]   montage of recent refs (prints the path)
  learn PLAYER --game GAME --target TARGET
  feedback PLAYER keep|drop "text" [--deliv D] [--clip C]
  output PLAYER GAME FILE...            record delivered files in the player's game history
  rm player|team ID
"""
import json, os, re, shutil, subprocess, sys, time
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hrstate

KINDS = {'player': 'players', 'team': 'teams'}
MAX_REFS_PER_KIT = 40


# ---------- storage ----------
def _dir(kind):
    d = os.path.join(hrstate.LIB, KINDS[kind]); os.makedirs(d, exist_ok=True); return d


def _path(kind, pid):
    return os.path.join(_dir('player'), pid, 'profile.json') if kind == 'player' \
        else os.path.join(_dir('team'), f'{pid}.json')


def refs_dir(pid):
    d = os.path.join(_dir('player'), pid, 'refs'); os.makedirs(d, exist_ok=True); return d


def exists(kind, pid):
    return os.path.exists(_path(kind, pid))


def load(kind, pid):
    p = _path(kind, pid)
    if not os.path.exists(p):
        sys.exit(f'hrprofile: no {kind} profile {pid!r} — `hrprofile.py list {KINDS[kind]}`')
    return json.load(open(p))


def save(kind, pid, data):
    data['id'] = pid; data['updated'] = time.strftime('%Y-%m-%d')
    hrstate._write(_path(kind, pid), data)


def all_(kind):
    d = _dir(kind); out = {}
    for f in sorted(os.listdir(d)):
        if kind == 'player' and os.path.exists(os.path.join(d, f, 'profile.json')):
            out[f] = json.load(open(os.path.join(d, f, 'profile.json')))
        elif kind == 'team' and f.endswith('.json'):
            out[f[:-5]] = json.load(open(os.path.join(d, f)))
    return out


# ---------- creation ----------
PLAYER_TEMPLATE = {
    'name': None, 'nickname': None, 'grad_year': None, 'sport': None, 'client_id': None,
    'lower_third': {'line1': None, 'line2': None},
    'appearance': {'hair': None, 'skin_tone': None, 'build': None, 'height': None, 'footwear': None,
                   'accessories': [], 'other': []},
    'teams': [], 'decoys': [], 'notes': [], 'flags': [], 'feedback': [],
    'refs': [], 'observations': [], 'id_stats': {}, 'style': {}, 'games': [], 'history': {},
}


def new_player(pid, name, team=None, number=None, grad=None, sport=None, client=None):
    p = json.loads(json.dumps(PLAYER_TEMPLATE))
    p.update(name=name, grad_year=grad, sport=sport, client_id=client)
    p['lower_third']['line1'] = name
    if team:
        p['teams'].append({'team_id': team, 'number': number, 'position': None, 'seasons': [], 'active': True})
    save('player', pid, p); refs_dir(pid); return p


def new_team(pid, name, sport=None, folder=None, color=None, client=None):
    t = {'name': name, 'sport': sport, 'client_id': client, 'media_folder': folder or name,
         'club': None, 'level': None,
         'kits': {'home': {'shirt': color, 'shorts': None, 'socks': None, 'hsv': {}}},
         'roster': {}, 'opponents': {}, 'notes': []}
    save('team', pid, t); return t


def kit_hsv(team_id, kit='home', encoding='canon_clog3'):
    """Calibrated shirt range for this kit on footage of this encoding (kits.<kit>.hsv.<encoding>)."""
    p = _path('team', team_id)
    if not os.path.exists(p):
        return None
    return ((json.load(open(p)).get('kits', {}).get(kit) or {}).get('hsv') or {}).get(encoding)


def membership(player, team_id=None):
    ts = player.get('teams', [])
    if team_id:
        hit = [t for t in ts if t['team_id'] == team_id]
        if hit:
            return hit[0]
    act = [t for t in ts if t.get('active')]
    return (act or ts or [None])[0]


def last_game(p):
    return max((g.get('date') or '' for g in p.get('games', [])), default='')


# ---------- references ----------
def _extract(src, t, box, out):
    """Crop a reference from the source at full resolution (box in source pixels), with headroom."""
    from PIL import Image, ImageOps
    tmp = os.path.join(hrstate.tmp('ref'), 'f.png')
    subprocess.run([hrstate.tool('ffmpeg'), '-nostdin', '-v', 'error', '-y', '-ss', f'{t:.3f}', '-i', src,
                    '-frames:v', '1', tmp], check=True)
    im = Image.open(tmp)
    x0, y0, x1, y1 = box; w, h = x1 - x0, y1 - y0
    x0, x1 = max(0, x0 - w * 0.25), min(im.width, x1 + w * 0.25)
    y0, y1 = max(0, y0 - h * 0.35), min(im.height, y1 + h * 0.15)
    c = ImageOps.autocontrast(im.crop((int(x0), int(y0), int(x1), int(y1))).convert('RGB'), cutoff=1)
    c.thumbnail((360, 480)); c.save(out, quality=90); shutil.rmtree(os.path.dirname(tmp), ignore_errors=True)
    return out


def ref_add(pid, src, t, box, kit=None, enc=None, cues=None, game=None, clip=None, date=None):
    p = load('player', pid)
    name = f"{(date or time.strftime('%Y-%m-%d'))}_{hrstate.slug(clip or os.path.basename(src))}_{t:.1f}.jpg"
    out = os.path.join(refs_dir(pid), name)
    _extract(src, float(t), [float(v) for v in box], out)
    p['refs'] = [r for r in p.get('refs', []) if r['file'] != name] + [
        {'file': name, 'date': date or time.strftime('%Y-%m-%d'), 'game': game, 'clip': clip, 't': t,
         'kit': kit, 'encoding': enc, 'cues': cues or []}]
    # keep the newest MAX_REFS_PER_KIT per kit
    by_kit = {}
    for r in sorted(p['refs'], key=lambda r: r['date'], reverse=True):
        by_kit.setdefault(r.get('kit'), []).append(r)
    keep = [r for rs in by_kit.values() for r in rs[:MAX_REFS_PER_KIT]]
    for r in p['refs']:
        if r not in keep:
            try:
                os.remove(os.path.join(refs_dir(pid), r['file']))
            except FileNotFoundError:
                pass
    p['refs'] = keep
    save('player', pid, p)
    return out


def refsheet(pid, out=None, kit=None, n=24):
    from PIL import Image, ImageDraw, ImageFont
    p = load('player', pid)
    refs = [r for r in sorted(p.get('refs', []), key=lambda r: r['date'], reverse=True)
            if not kit or r.get('kit') == kit][:n]
    if not refs:
        return None
    TW, TH, COLS = 180, 240, 8
    rows = (len(refs) + COLS - 1) // COLS
    sheet = Image.new('RGB', (COLS * TW, rows * (TH + 34) + 30), (15, 15, 15)); d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 14)
    except OSError:
        font = ImageFont.load_default()
    m = membership(p) or {}
    d.text((6, 6), f"{p['name']} #{m.get('number', '?')} — reference sightings (newest first)", fill=(255, 255, 0), font=font)
    for i, r in enumerate(refs):
        try:
            im = Image.open(os.path.join(refs_dir(pid), r['file'])); im.thumbnail((TW, TH))
        except FileNotFoundError:
            continue
        x, y = (i % COLS) * TW, 30 + (i // COLS) * (TH + 34)
        sheet.paste(im, (x + (TW - im.width) // 2, y))
        d.text((x + 3, y + TH + 2), f"{r['date']} {r.get('kit') or ''}", fill=(0, 255, 255), font=font)
        d.text((x + 3, y + TH + 17), ','.join(r.get('cues', []))[:24], fill=(200, 200, 200), font=font)
    out = out or os.path.join(_dir('player'), pid, 'refsheet.jpg')
    sheet.save(out, quality=88); return out


# ---------- learning ----------
def _aggregate(p):
    """id_stats and style are sums over history[game] — so re-learning a game is idempotent."""
    cues_ok, cues_bad, events, feet, positions, areas = Counter(), Counter(), Counter(), Counter(), Counter(), Counter()
    for h in p.get('history', {}).values():
        cues_ok.update(h.get('cues_confirmed', {})); cues_bad.update(h.get('misled_by', {}))
        events.update(h.get('events', {})); feet.update(h.get('foot', {}))
        positions.update(h.get('positions', {})); areas.update(h.get('areas', {}))
    n = sum(1 for h in p.get('history', {}).values() if h.get('confirmed'))
    total_conf = sum(h.get('confirmed', 0) for h in p.get('history', {}).values()) or 1
    p['id_stats'] = {'games': n, 'sightings': total_conf,
                     'cues': {c: {'confirmed': k, 'rate': round(k / total_conf, 2)} for c, k in cues_ok.most_common()},
                     'misled_by': dict(cues_bad.most_common())}
    p['style'] = {'events': dict(events.most_common()), 'foot_or_hand': dict(feet.most_common()),
                  'positions': dict(positions.most_common()), 'areas': dict(areas.most_common())}


def _differs(a, b):
    """True when two appearance descriptions share under half their words (a real change, not rewording)."""
    stop = {'a', 'an', 'the', 'in', 'with', 'and', 'usually', 'often', 'her', 'his', 'their', 'of'}
    wa = {w for w in re.findall(r'[a-z]+', a.lower()) if w not in stop}
    wb = {w for w in re.findall(r'[a-z]+', b.lower()) if w not in stop}
    return bool(wa and wb) and len(wa & wb) / min(len(wa), len(wb)) < 0.5


def learn(pid, game, target):
    p = load('player', pid)
    gdir = hrstate.game_dir(game); g = hrstate._read(os.path.join(gdir, 'game.json'), {})
    t = hrstate._read(os.path.join(gdir, 'targets', target, 'find.json'), {})
    if t.get('player_id') not in (None, pid):
        sys.exit(f'target {target} is for {t.get("player_id")}, not {pid}')
    side = t.get('side') or 'home'; team = g.get('teams', {}).get(side, {})
    kit = team.get('kit'); gid = g.get('id', os.path.basename(gdir)); date = g.get('date')
    clips = t.get('clips', {}); media = g.get('media', {}).get('clips', {})
    conf = {c: v for c, v in clips.items() if v.get('status') == 'CONFIRMED'}

    h = {'date': date, 'event': g.get('event'), 'team_id': team.get('team_id'), 'kit': kit,
         'confirmed': len(conf), 'cues_confirmed': {}, 'misled_by': {}, 'events': {}, 'foot': {},
         'positions': {}, 'areas': {}}
    for c, v in clips.items():
        if v.get('status') == 'CONFIRMED':
            for cue in v.get('cues', []):
                h['cues_confirmed'][cue] = h['cues_confirmed'].get(cue, 0) + 1
        for m in v.get('misled_by', []):
            h['misled_by'][m] = h['misled_by'].get(m, 0) + 1
        if v.get('status') == 'CONFIRMED' and (v.get('score') or 0) >= 2:
            ev = v.get('event') or 'other'; h['events'][ev] = h['events'].get(ev, 0) + 1
            for k, field in (('foot', 'foot'), ('foot', 'hand'), ('positions', 'position'), ('areas', 'area')):
                if v.get(field):
                    h[k][v[field]] = h[k].get(v[field], 0) + 1
    p.setdefault('history', {})[gid] = h

    # references: one per confirmed clip that recorded a ref box
    made = 0
    for c, v in conf.items():
        r = v.get('ref')
        if r and media.get(c, {}).get('path'):
            ref_add(pid, media[c]['path'], float(r['t']), r['box'], kit, media[c].get('encoding'),
                    v.get('cues', []), gid, c, date)
            made += 1
    p = load('player', pid); p['history'][gid] = h     # ref_add saved; re-apply history

    # appearance observations (dated); fill blanks, flag conflicts
    for c, v in conf.items():
        for field, val in (v.get('observed') or {}).items():
            obs = {'date': date, 'game': gid, 'field': field, 'value': val}
            if obs not in p['observations']:
                p['observations'].append(obs)
            cur = p['appearance'].get(field)
            if cur in (None, '', []):
                p['appearance'][field] = val
            elif isinstance(cur, str) and _differs(cur, val):
                flag = f"{date}: {field} looked like '{val}' (profile says '{cur}') — update if it changed"
                if flag not in p['flags']:
                    p['flags'].append(flag)
    # number seen on a different team / number than the profile
    m = membership(p, team.get('team_id'))
    if team.get('team_id') and not m:
        p['teams'].append({'team_id': team['team_id'], 'number': t.get('number'), 'position': None,
                           'seasons': [], 'active': True})
    for d in t.get('decoys_met', []):
        if d not in p['decoys']:
            p['decoys'].append(d)

    best = {c: v.get('beat') or v.get('event') for c, v in conf.items() if (v.get('score') or 0) >= 3}
    entry = {'game': gid, 'date': date, 'event': g.get('event'), 'team_id': team.get('team_id'),
             'sport': g.get('sport'), 'confirmed': len(conf), 'best_clips': best,
             'sources': g.get('sources', []), 'outputs': []}   # originals, not the work dir (deleted at clean)
    same = [x for x in p['games'] if x.get('game') == gid or (x.get('date') == date and not x.get('sources')
            and not x.get('game_dir') and (x.get('event') or '').lower() in (g.get('event') or '').lower())]
    for old in same:     # merge earlier records of this game (re-learn, or a pre-v1 entry)
        entry['outputs'] = sorted(set(entry['outputs']) | set(old.get('outputs', [])))
        entry['best_clips'] = {**old.get('best_clips', {}), **entry['best_clips']}
        entry['sources'] = entry['sources'] or old.get('sources', [])
        p['games'].remove(old)
    p['games'].append(entry); p['games'].sort(key=lambda x: x.get('date') or '')
    if g.get('sport') and not p.get('sport'):
        p['sport'] = g['sport']
    _aggregate(p); save('player', pid, p)
    return {'refs_added': made, 'confirmed': len(conf), 'best': len(best), 'flags': p['flags'][-3:]}


def add_output(pid, game, path):
    p = load('player', pid)
    for x in p['games']:
        if x.get('game') == game and path not in x.setdefault('outputs', []):
            x['outputs'].append(path)
    save('player', pid, p)


# ---------- brief ----------
def brief(pid, team_id=None):
    p = load('player', pid); m = membership(p, team_id) or {}
    t = load('team', m['team_id']) if m.get('team_id') and exists('team', m['team_id']) else {}
    kits = t.get('kits', {})
    look = '; '.join(f'{k}: ' + (', '.join(v) if isinstance(v, list) else str(v))
                     for k, v in p.get('appearance', {}).items() if v)
    st = p.get('id_stats', {}); cues = st.get('cues', {})
    lines = [f"{p['name']}" + (f" ({p['nickname']})" if p.get('nickname') else '')
             + f" — #{m.get('number', '?')} for {t.get('name', m.get('team_id', '?'))}"
             + (f", {m['position']}" if m.get('position') else '') + (f" — {p['sport']}" if p.get('sport') else ''),
             '  kits: ' + ('; '.join(f"{k}: {v.get('shirt')}" for k, v in kits.items()) or '?'),
             f"  look: {look or '(nothing recorded yet — identify by number, record what you see)'}"]
    if cues:
        lines.append(f"  best cues ({st.get('sightings')} sightings over {st.get('games')} games): "
                     + ', '.join(f"{c} {v['rate']:.0%}" for c, v in cues.items()))
    if st.get('misled_by'):
        lines.append('  misled by: ' + ', '.join(f'{k} ×{v}' for k, v in st['misled_by'].items()))
    lines.append(f"  decoys: {'; '.join(p.get('decoys', [])) or 'none recorded'}")
    if p.get('refs'):
        lines.append(f"  reference crops: {len(p['refs'])} (hrprofile.py refsheet {pid})")
    ev = (p.get('style') or {}).get('events')
    if ev:
        lines.append('  style: ' + ', '.join(f'{k} ×{v}' for k, v in ev.items())
                     + ('; ' + ', '.join(f'{k} ×{v}' for k, v in p['style']['foot_or_hand'].items())
                        if p['style'].get('foot_or_hand') else ''))
    if t.get('roster'):
        lines.append('  team numbers: ' + ', '.join(f'#{k} {v}' for k, v in t['roster'].items()))
    for f in p.get('feedback', [])[-5:]:
        lines.append(f"  client {f['verdict']}: {f['text']}")
    for f in p.get('flags', []):
        lines.append(f"  ! {f}")
    for n in p.get('notes', [])[-5:]:
        lines.append(f"  note {n['date']}: {n['text']}")
    if p.get('games'):
        lines.append(f"  games processed: {len(p['games'])}, last {last_game(p)}")
    return '\n'.join(lines)


def _set(d, key, value, merge=False):
    cur = d; ks = key.split('.')
    for k in ks[:-1]:
        cur = cur.setdefault(k, {})
    if merge and isinstance(value, dict) and isinstance(cur.get(ks[-1]), dict):
        hrstate._deep_merge(cur[ks[-1]], value)
    else:
        cur[ks[-1]] = value


def _opts(a):
    return dict(zip(a[0::2], a[1::2]))


def main(a):
    if not a:
        print(__doc__); return
    cmd = a[0]
    if cmd == 'list':
        kinds = [k for k in ('player', 'team') if len(a) < 2 or a[1] in (k, k + 's', '--recent')]
        for kind in kinds:
            items = list(all_(kind).items())
            if kind == 'player' and '--recent' in a:
                items.sort(key=lambda kv: last_game(kv[1]), reverse=True)
            print(KINDS[kind] + ':')
            for pid, d in items:
                if kind == 'player':
                    m = membership(d) or {}
                    print(f"  {pid:18s} {d['name']:26s} #{str(m.get('number', '?')):3s} {m.get('team_id') or '':16s} "
                          f"{d.get('sport') or '':10s} games={len(d.get('games', []))} last={last_game(d) or '-'} "
                          f"refs={len(d.get('refs', []))}")
                else:
                    print(f"  {pid:18s} {d['name']:26s} {d.get('sport') or '':10s} "
                          f"{(d.get('kits', {}).get('home') or {}).get('shirt') or ''}")
    elif cmd == 'show':
        print(json.dumps(load(a[1], a[2]), indent=2))
    elif cmd == 'brief':
        print(brief(a[1], a[2] if len(a) > 2 else None))
    elif cmd == 'new':
        kind, pid = a[1], a[2]; o = _opts(a[3:])
        if exists(kind, pid):
            sys.exit(f'{kind} {pid} exists — use set/merge')
        if kind == 'player':
            new_player(pid, o['--name'], o.get('--team'), int(o['--number']) if o.get('--number') else None,
                       int(o['--grad']) if o.get('--grad') else None, o.get('--sport'), o.get('--client'))
        else:
            new_team(pid, o['--name'], o.get('--sport'), o.get('--folder'), o.get('--color'), o.get('--client'))
        print(_path(kind, pid))
    elif cmd in ('set', 'merge'):
        kind, pid, key = a[1], a[2], a[3]; d = load(kind, pid)
        if cmd == 'set':
            try:
                v = json.loads(a[4])
            except json.JSONDecodeError:
                v = a[4]
        else:
            v = json.load(open(a[4]))
        _set(d, key, v, merge=cmd == 'merge'); save(kind, pid, d)
    elif cmd == 'note':
        kind, pid = a[1], a[2]; d = load(kind, pid)
        d.setdefault('notes', []).append({'date': time.strftime('%Y-%m-%d'), 'text': ' '.join(a[3:])})
        save(kind, pid, d)
    elif cmd == 'ref' and a[1] == 'add':
        o = _opts(a[3:])
        print(ref_add(a[2], o['--src'], float(o['--t']), o['--box'].split(','), o.get('--kit'), o.get('--enc'),
                      o['--cues'].split(',') if o.get('--cues') else [], o.get('--game'), o.get('--clip')))
    elif cmd == 'refsheet':
        o = _opts(a[2:])
        print(refsheet(a[1], o.get('--out'), o.get('--kit'), int(o.get('--n', 24))) or 'no refs yet')
    elif cmd == 'learn':
        o = _opts(a[2:]); print(json.dumps(learn(a[1], o['--game'], o['--target']), indent=2))
    elif cmd == 'feedback':
        pid, verdict, text = a[1], a[2], a[3]; o = _opts(a[4:]); d = load('player', pid)
        d.setdefault('feedback', []).append({'date': time.strftime('%Y-%m-%d'), 'verdict': verdict, 'text': text,
                                             'deliv': o.get('--deliv'), 'clip': o.get('--clip')})
        save('player', pid, d)
    elif cmd == 'output':
        for f in a[3:]:
            add_output(a[1], a[2], f)
    elif cmd == 'rm':
        p = _path(a[1], a[2])
        shutil.rmtree(os.path.dirname(p)) if a[1] == 'player' else os.remove(p)
        print('removed', a[1], a[2])
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main(sys.argv[1:])
