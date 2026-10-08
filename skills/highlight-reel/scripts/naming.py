"""Output paths for a deliverable, one per aspect, from a template.

Template order: the deliverable's client (library/clients/<id>.json → output_template), else the machine
config `output_template`, else DEFAULT. Paths are relative to the client's `output_root`, else the config
output_folder. Never overwrites: an existing file gets _v2, _v3 ….

Fields: {client} {season} {team} {opponent} {date} {event} {sport} {who} {player} {number} {type} {aspect} {deliv}

Usage: python3 naming.py [DELIV_ID]      prints {aspect: path} for the current (or given) deliverable"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hrstate

DEFAULT = '{team}/{date} {event}/{who}_{type}_{aspect}.mp4'


def _clean(s):
    return re.sub(r'[\\/:*?"<>|]+', '-', str(s)).strip() if s is not None else ''


def season_of(date):
    y, m = int(date[:4]), int(date[5:7])
    return f'{y} Spring' if m <= 6 else f'{y} Fall'


def fields(did=None):
    d = hrstate.load('deliv', did); g = hrstate.load('game')
    t = hrstate._read(os.path.join(hrstate.game_dir(), 'targets', d['target'], 'find.json'), {})
    side = t.get('side', 'home'); other = 'away' if side == 'home' else 'home'
    team = g['teams'][side]; who = team['name']; player = number = ''
    if t.get('player_id'):
        import hrprofile
        p = hrprofile.load('player', t['player_id'])
        m = hrprofile.membership(p, team.get('team_id')) or {}
        player, number = p['name'], m.get('number') or ''
        who = f"{player.split()[-1]}_{number}" if number != '' else player
    client = {}
    if d.get('client_id'):
        client = hrstate._read(os.path.join(hrstate.LIB, 'clients', f"{d['client_id']}.json"), {})
    return d, client, {
        'client': client.get('name', ''), 'season': season_of(g['date']), 'team': team['name'],
        'opponent': g['teams'][other]['name'], 'date': g['date'], 'event': g.get('event', ''),
        'sport': g.get('sport', ''), 'who': who, 'player': player, 'number': number,
        'type': d['type'], 'deliv': d['id']}


def paths(did=None):
    d, client, f = fields(did)
    tpl = client.get('output_template') or hrstate.config('output_template') or DEFAULT
    root = os.path.expanduser(client.get('output_root') or hrstate.config('output_folder'))
    out = {}
    for asp in d.get('aspects', ['9:16']):
        rel = tpl.format(**{k: _clean(v) for k, v in {**f, 'aspect': asp.replace(':', 'x')}.items()})
        p = os.path.join(root, rel); base, ext = os.path.splitext(p); n = 2
        while os.path.exists(p):
            p = f'{base}_v{n}{ext}'; n += 1
        out[asp] = p
    return out


if __name__ == '__main__':
    print(json.dumps(paths(sys.argv[1] if len(sys.argv) > 1 else None), indent=2))
