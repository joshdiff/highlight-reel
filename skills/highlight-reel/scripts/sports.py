"""Sport packs: <repo>/sports/<sport>/pack.json (machine-readable) + pack.md (craft rules for find,
select and direct). Stages load the pack for the game's sport.

Usage: python3 sports.py list | show SPORT | events SPORT | deliverable SPORT TYPE"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SPORTS_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', '..', 'sports'))
ALIASES = {'goals_reel': 'scoring_reel'}


def available():
    return sorted(d for d in os.listdir(SPORTS_DIR) if os.path.exists(os.path.join(SPORTS_DIR, d, 'pack.json')))


def load(sport):
    p = os.path.join(SPORTS_DIR, sport or '', 'pack.json')
    if not sport or not os.path.exists(p):
        sys.exit(f'sports: no pack for {sport!r}; available: {available()}')
    d = json.load(open(p)); d['doc'] = os.path.join(SPORTS_DIR, sport, 'pack.md')
    return d


def current():
    import hrstate
    return load(hrstate.get('sport'))


def deliverable(pack, dtype):
    return pack['deliverables'].get(ALIASES.get(dtype, dtype)) or sys.exit(
        f"sports: {pack['id']} has no deliverable {dtype!r} ({list(pack['deliverables'])})")


def surface(pack=None):
    try:
        return (pack or current()).get('surface', {})
    except SystemExit:
        return {}


if __name__ == '__main__':
    a = sys.argv[1:] or ['list']
    if a[0] == 'list':
        for s in available():
            p = load(s); print(f"  {s:12s} {p['name']:12s} events: {', '.join(list(p['events'])[:8])}…")
    elif a[0] == 'show':
        print(json.dumps(load(a[1]), indent=2))
    elif a[0] == 'events':
        for k, v in load(a[1])['events'].items():
            print(f"  {v['score']}  {k:18s} {v['label']}" + ('  [scoring]' if v.get('scoring') else ''))
    elif a[0] == 'deliverable':
        print(json.dumps(deliverable(load(a[1]), a[2]), indent=2))
