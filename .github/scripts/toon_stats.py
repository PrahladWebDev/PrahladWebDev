#!/usr/bin/env python3
"""
Generates two cartoon-themed SVGs for the profile README, from live GitHub data:
  assets/generated/toon-trophies.svg   (Trophy Shelf)
  assets/generated/toon-activity.svg   (Contribution Activity graph)
No third-party service is used: only the GitHub GraphQL API (via the Actions token).

Usage:  GITHUB_TOKEN=... GH_USER=PrahladWebDev python .github/scripts/toon_stats.py
        python .github/scripts/toon_stats.py --demo      # fake data, for a local look-test only
"""
import json, os, sys, datetime, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(ROOT, 'assets', 'generated')
G = json.load(open(os.path.join(HERE, 'fredoka-glyphs.json'), encoding='utf-8'))
UPM = G['upm']

INK='#8f89d4'; SH='#05070f'; TXT='#ece9ff'; CARD='#141b33'; CREAM=CARD; MUTED='#a7a3c9'   # Midnight theme: outline / shadow / text / card
BR_PINK='#ffc2d4'; BR_BUTTER='#ffe9a6'; BR_MINT='#bfeedd'; BR_SKY='#bfe3ff'; BR_LILAC='#dccfff'
def _mix(a, b=CARD, k=.46):
    A=[int(a[i:i+2],16) for i in (1,3,5)]; B=[int(b[i:i+2],16) for i in (1,3,5)]
    return '#%02x%02x%02x' % tuple(round(B[j]*(1-k)+A[j]*k) for j in range(3))
PINK=_mix(BR_PINK); BUTTER=_mix(BR_BUTTER); MINT=_mix(BR_MINT); SKY=_mix(BR_SKY); LILAC=_mix(BR_LILAC)
ACCENT='#f2a93b'
STAR='M0-11 L3.2-3.2 L11 0 L3.2 3.2 L0 11 L-3.2 3.2 L-11 0 L-3.2-3.2Z'

# ───────────── text as outlines (Fredoka Bold) ─────────────
def width(t, size, tr=0):
    return sum(G['adv'].get(c, 0) * size / UPM + tr for c in t) - tr

def run(t, size, x, y, anchor='start', tr=0):
    """returns (svg <g> with glyph paths, width). fill/stroke are set by the caller via wrapper attrs."""
    w = width(t, size, tr); s = size / UPM
    if anchor == 'middle': x -= w / 2
    elif anchor == 'end': x -= w
    parts = []; cx = 0
    for c in t:
        d = G['d'].get(c)
        if d: parts.append(f'<path transform="translate({cx:.0f} 0)" d="{d}"/>')
        cx += G['adv'].get(c, 0) + tr * UPM / size
    return f'<g transform="translate({x:.1f} {y:.1f}) scale({s:.5f} {-s:.5f})">{"".join(parts)}</g>', w

def text(t, size, x, y, fill=TXT, anchor='start', tr=0):
    g, w = run(t, size, x, y, anchor, tr)
    return g.replace('<g ', f'<g fill="{fill}" ', 1), w

def sticker(t, size, x, y, fill='#fff', anchor='middle', sw=None, sh=None):
    sw = sw or size * 0.11; sh = sh or size * 0.06; s = size / UPM
    g, w = run(t, size, x, y, anchor)
    wsw = sw / s
    gs_, _ = run(t, size, (x if anchor == 'start' else x) + sh, y + sh * 1.15, anchor)
    gs_ = gs_.replace('<g ', f'<g fill="{SH}" stroke="{SH}" stroke-width="{wsw:.0f}" stroke-linejoin="round" ', 1)
    gm = g.replace('<g ', f'<g fill="{fill}" stroke="{INK}" stroke-width="{wsw:.0f}" stroke-linejoin="round" paint-order="stroke fill" ', 1)
    return gs_ + gm, w

CSS = '''<style>
@keyframes bob{0%,100%{transform:translateY(0)}50%{transform:translateY(-5px)}}
.b{animation:bob 3.4s ease-in-out infinite}
@media (prefers-reduced-motion:reduce){.b{animation:none}}
</style>'''

def svg(w, h, body, defs=''):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img">{CSS}<defs>{defs}</defs>{body}</svg>'

def card(w, h, x=10, y=10, r=30, sh=7, fill=CREAM):
    return (f'<rect x="{x+sh}" y="{y+sh}" width="{w}" height="{h}" rx="{r}" fill="{SH}"/>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{INK}" stroke-width="3.5"/>')

def compact(n):
    n = int(n)
    return f'{n/1000:.1f}k'.replace('.0k', 'k') if n >= 1000 else str(n)

# ───────────── GitHub data ─────────────
QUERY = '''
query($login:String!, $after:String) {
  user(login:$login) {
    followers { totalCount }
    pullRequests { totalCount }
    issues { totalCount }
    repositories(ownerAffiliations:OWNER, isFork:false, first:100, after:$after) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes { stargazerCount primaryLanguage { name } }
    }
    contributionsCollection {
      totalCommitContributions
      contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }
    }
  }
}'''

def gql(login, token, after=None):
    req = urllib.request.Request('https://api.github.com/graphql',
        data=json.dumps({'query': QUERY, 'variables': {'login': login, 'after': after}}).encode(),
        headers={'Authorization': f'bearer {token}', 'Content-Type': 'application/json', 'User-Agent': 'toon-stats'})
    with urllib.request.urlopen(req, timeout=30) as r: d = json.load(r)
    if 'errors' in d: raise RuntimeError(d['errors'])
    return d['data']['user']

def fetch(login, token):
    u = gql(login, token); stars = 0; langs = set(); nodes = u['repositories']['nodes']; page = u['repositories']['pageInfo']
    while True:
        for n in nodes:
            stars += n['stargazerCount']
            if n['primaryLanguage']: langs.add(n['primaryLanguage']['name'])
        if not page['hasNextPage']: break
        nxt = gql(login, token, page['endCursor'])['repositories']; nodes, page = nxt['nodes'], nxt['pageInfo']
    cal = u['contributionsCollection']['contributionCalendar']
    days = [d for w in cal['weeks'] for d in w['contributionDays']]
    return {
        'Stars': stars, 'Commits': u['contributionsCollection']['totalCommitContributions'],
        'Followers': u['followers']['totalCount'], 'Repos': u['repositories']['totalCount'],
        'Pull Requests': u['pullRequests']['totalCount'], 'Issues': u['issues']['totalCount'],
        'Languages': len(langs), 'days': days, 'year_total': cal['totalContributions'],
    }

def demo():
    import random; random.seed(3); today = datetime.date.today()
    days = [{'date': (today - datetime.timedelta(days=i)).isoformat(), 'contributionCount': random.choice([0,0,1,2,3,5,8,4,6,2,0,9,12])} for i in range(60, -1, -1)]
    return {'Stars': 14, 'Commits': 842, 'Followers': 23, 'Repos': 31, 'Pull Requests': 9, 'Issues': 4, 'Languages': 6, 'days': days, 'year_total': 1234}

# ───────────── Trophy shelf ─────────────
# thresholds for ranks  C  B  A  AA  AAA  S
TIERS = {'Stars': [1,5,15,40,100,300], 'Commits': [1,100,300,700,1500,3000], 'Followers': [1,5,15,40,100,300],
         'Repos': [1,5,15,30,60,100], 'Pull Requests': [1,5,15,40,100,250], 'Issues': [1,5,15,40,100,250], 'Languages': [1,3,5,8,12,16]}
RANKS = ['C','B','A','AA','AAA','S']

def rank(metric, v):
    r = -1
    for i, t in enumerate(TIERS[metric]):
        if v >= t: r = i
    return RANKS[r] if r >= 0 else '–'

def cup(cx, cy, got):
    gold = '#ffd45e' if got else '#3a4270'
    st = f'stroke="{INK}" stroke-width="3.5" stroke-linejoin="round" stroke-linecap="round"'
    return (f'<g transform="translate({cx} {cy})">'
            f'<path d="M-22 -18 C-40 -18 -40 4 -21 6" fill="none" {st}/><path d="M22 -18 C40 -18 40 4 21 6" fill="none" {st}/>'
            f'<path d="M-4 20 H4 V31 H-4Z" fill="{gold}" {st}/><path d="M-17 31 H17 Q19 31 19 34 V39 H-19 V34 Q-19 31 -17 31Z" fill="{gold}" {st}/>'
            f'<path d="M-23 -29 H23 V-6 C23 11 12 21 0 21 C-12 21 -23 11 -23 -6Z" fill="{gold}" {st}/>'
            f'<path d="{STAR}" fill="#fff" stroke="{INK}" stroke-width="2.4" stroke-linejoin="round" transform="translate(0 -8) scale(.95)"/></g>')

def trophies(d):
    metrics = ['Stars','Commits','Followers','Repos','Pull Requests','Issues','Languages']
    cols = [PINK, BUTTER, MINT, SKY, LILAC, PINK, BUTTER]
    cw, gap, ch = 150, 14, 206; W = 7 * cw + 6 * gap + 40; H = ch + 40
    body = ''
    for i, (m, c) in enumerate(zip(metrics, cols)):
        x = 20 + i * (cw + gap); y = 14; v = d[m]; r = rank(m, v); got = r != '–'
        rot = (-1.2, 1.0)[i % 2]
        inner = card(cw, ch, 0, 0, r=26, sh=5, fill=c)
        inner += f'<g class="b" style="animation-delay:{-i*0.45:.2f}s">{cup(cw/2, 64, got)}</g>'
        t, _ = sticker(compact(v), 34, cw/2, 140, anchor='middle'); inner += t
        t, _ = text(m.upper(), 13, cw/2, 168, fill=TXT, anchor='middle', tr=1.1); inner += t
        # rank badge
        rw = max(34, width(r, 16) + 20)
        inner += (f'<rect x="{cw-rw-8+2}" y="12" width="{rw}" height="26" rx="13"  fill="{SH}"/><rect x="{cw-rw-8}" y="10" width="{rw}" height="26" rx="13" fill="#0b1020" stroke="{INK}" stroke-width="3"/>')
        t, _ = text(r, 16, cw-8-rw/2, 29, anchor='middle'); inner += t
        body += f'<g transform="translate({x} {y}) rotate({rot} {cw/2} {ch/2})">{inner}</g>'
    return svg(W, H, body)

# ───────────── Activity graph ─────────────
def activity(d, n=30):
    days = d['days'][-n:]; counts = [x['contributionCount'] for x in days]
    W, H = 1200, 340; cw, ch = 1170, 310
    px0, px1, py0, py1 = 100, 1140, 118, 262
    mx = max(5, max(counts)); step = max(1, -(-mx // 4)); top = step * 4
    xs = [px0 + i * (px1 - px0) / (len(days) - 1) for i in range(len(days))]
    ys = [py1 - c / top * (py1 - py0) for c in counts]
    body = card(cw, ch, r=32)
    t, _ = sticker('Contribution Activity', 32, 44, 66, anchor='start'); body += t
    total = sum(counts); label = f'{total} contributions · last {len(days)} days'
    lw = width(label, 18) + 44; lx = 10 + cw - lw - 28
    body += f'<rect x="{lx+3}" y="{34+4}" width="{lw:.0f}" height="40"  rx="20" fill="{SH}"/><rect x="{lx}" y="34" width="{lw:.0f}" height="40" rx="20" fill="{MINT}" stroke="{INK}" stroke-width="3"/>'
    t, _ = text(label, 18, lx + lw/2, 60, anchor='middle'); body += t
    # grid + y labels
    for k in range(5):
        v = k * step; y = py1 - v / top * (py1 - py0)
        body += f'<line x1="{px0}" x2="{px1}" y1="{y:.1f}" y2="{y:.1f}" stroke="{INK}" stroke-opacity=".28" stroke-width="2" stroke-dasharray="2 9" stroke-linecap="round"/>'
        t, _ = text(str(v), 15, px0 - 16, y + 5, fill=MUTED, anchor='end'); body += t
    # area + line
    pts = ' '.join(f'{x:.1f},{y:.1f}' for x, y in zip(xs, ys))
    body += f'<polygon points="{xs[0]:.1f},{py1} {pts} {xs[-1]:.1f},{py1}" fill="{BR_PINK}" fill-opacity=".22"/>'
    body += f'<polyline points="{pts}" fill="none" stroke="{SH}" stroke-width="9" stroke-linejoin="round" stroke-linecap="round"/>'
    body += f'<polyline points="{pts}" fill="none" stroke="{ACCENT}" stroke-width="5" stroke-linejoin="round" stroke-linecap="round"/>'
    for x, y, c in zip(xs, ys, counts):
        body += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{6 if c else 4}" fill="{"#fff" if c else CARD}" stroke="{INK}" stroke-width="3"/>'
    # x labels
    for i in range(0, len(days), 5):
        dt = datetime.date.fromisoformat(days[i]['date']); t, _ = text(dt.strftime('%b ') + str(dt.day), 14, xs[i], py1 + 32, fill=MUTED, anchor='middle'); body += t
    return svg(W, H, body)

def placeholder(title, sub, w=1200, h=140):
    body = card(w - 30, h - 30, r=28)
    t, _ = sticker(title, 30, w/2, h/2 - 2, anchor='middle'); body += t
    t, _ = text(sub, 16, w/2, h/2 + 32, fill=MUTED, anchor='middle'); body += t
    return svg(w, h, body)

def main():
    os.makedirs(OUT, exist_ok=True)
    if '--placeholder' in sys.argv:
        open(os.path.join(OUT, 'toon-trophies.svg'), 'w', encoding='utf-8').write(placeholder('Trophy Shelf is warming up', "Run the 'Update Toon Stats' workflow once (Actions tab)"))
        open(os.path.join(OUT, 'toon-activity.svg'), 'w', encoding='utf-8').write(placeholder('Activity graph is warming up', "Run the 'Update Toon Stats' workflow once (Actions tab)"))
        return
    if '--demo' in sys.argv: data = demo()
    else:
        token = os.environ.get('GITHUB_TOKEN'); user = os.environ.get('GH_USER')
        if not token or not user: sys.exit('GITHUB_TOKEN and GH_USER are required')
        data = fetch(user, token)
    open(os.path.join(OUT, 'toon-trophies.svg'), 'w', encoding='utf-8').write(trophies(data))
    open(os.path.join(OUT, 'toon-activity.svg'), 'w', encoding='utf-8').write(activity(data))
    print('written', OUT)

if __name__ == '__main__': main()
