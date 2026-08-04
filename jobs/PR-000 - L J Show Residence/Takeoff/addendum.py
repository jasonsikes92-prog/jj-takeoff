# -*- coding: utf-8 -*-
import sys, json, re, math
RB = json.load(open(r'C:\Users\jason\.claude\skills\jnj-estimate-takeoff\reference\rate_book.json'))
L = RB['lines']
matched = [tuple(m) for m in json.load(open('matched.json'))]
have = {m[0] for m in matched}

HEATED = 3245.7; GARAGE = 1038.5; UNDER = 5529.8; COVERED = 1245.6
FASCIA = 456.2; WINDOWS = 22
ADD = []
def add(i, qty, note=''):
    if i in have:
        return
    ADD.append((i, round(float(qty), 2), note)); have.add(i)

# ---- fix: the ALLOWANCE 'Windows' line (index 93) was shadowed by an ASSEMBLY row
add(93, WINDOWS, 'window units counted off plan + all 4 elevations')

# ---- PAINT
add(552, HEATED, 'interior paint on heated SF')
add(553, GARAGE, 'garage paint')
add(554, HEATED + GARAGE, 'exterior paint on heated + garage')

# ---- GARAGE DOORS (3 x 10080 carriage-style)
add(566, 3); add(567, 3); add(568, 3)

# ---- GUTTERS
add(548, FASCIA, 'full measured roof edge')
add(549, 140, 'downspouts')
add(551, FASCIA, 'leaf protection')

# ---- CLEANING / PUNCH
add(597, HEATED + GARAGE); add(599, HEATED + GARAGE)
add(600, WINDOWS); add(602, HEATED)

# ---- LANDSCAPING
add(592, 1); add(596, 1)

# ---- FLOORING  (heated split: LVP living, tile wet rooms)
TILE_SF = 780.0; LVP_SF = HEATED - TILE_SF
add(546, round(LVP_SF * 1.05, 1), 'LVP to living areas +5%')
add(547, round(LVP_SF * 1.05, 1))
add(270, round(TILE_SF * 1.10, 1), 'tile to wet rooms +10%')
add(271, round(TILE_SF * 1.10, 1))
add(272, round(TILE_SF * 1.10, 1))

# ---- LIGHTING / ELECTRICAL EXTRAS
add(244, 1)                       # under-cabinet LED
add(174, 1)                       # generator pre-wire

# ---- BATHS 1-4 (template carries 4; this house has 5 full + 1 powder -> flagged)
BATH = {
    '1': dict(vanity_lf=12, tile_wall=130, floor=140, niche=2, bench=1, glass='master'),
    '2': dict(vanity_lf=5,  tile_wall=85,  floor=60,  niche=1, bench=0, glass='framed'),
    '3': dict(vanity_lf=5,  tile_wall=85,  floor=55,  niche=1, bench=0, glass='framed'),
    '4': dict(vanity_lf=5,  tile_wall=85,  floor=50,  niche=1, bench=0, glass='framed'),
}
for i, l in enumerate(L):
    if i in have or str(l.get('cost_type')) == 'ASSEMBLY' or not l.get('unit_cost'):
        continue
    grp = str(l.get('group') or ''); nm = str(l.get('name') or '')
    m = re.search(r'Bath (\d)', grp) or re.search(r'Bath (\d)', nm)
    if not m:
        continue
    b = m.group(1)
    if b not in BATH:
        continue
    cfg = BATH[b]
    low = nm.lower()
    if 'toilet' in low: add(i, 1)
    elif 'vanity cabinets' in low and 'hardware' not in low and 'install' not in low: add(i, cfg['vanity_lf'])
    elif 'vanity cabinets - hardware' in low: add(i, cfg['vanity_lf'])
    elif 'vanity cabinets - installation' in low: add(i, cfg['vanity_lf'])
    elif 'granite or quartz' in low: add(i, round(cfg['vanity_lf'] * 2.25, 1))
    elif 'vanity sink' in low and 'faucet' not in low and 'mirror' not in low and 'drain' not in low:
        add(i, 2 if b == '1' else 1)
    elif 'faucet' in low: add(i, 2 if b == '1' else 1)
    elif 'mirror' in low: add(i, 2 if b == '1' else 1)
    elif 'towel bar' in low or 'install towel' in low: add(i, 2)
    elif 'light fixture' in low: add(i, 2 if b == '1' else 1)
    elif 'drain kit' in low: add(i, 2 if b == '1' else 1)
    elif 'cutout' in low: add(i, 2 if b == '1' else 1)
    elif 'shower valve' in low: add(i, 1)
    elif 'shower surround fiberglass' in low: continue          # tiled, not fiberglass
    elif 'tile walls' in low and 'material' in low: add(i, cfg['tile_wall'])
    elif 'tile sundries' in low: add(i, cfg['tile_wall'])
    elif 'schluter' in low: add(i, cfg['tile_wall'])
    elif 'tile wall labor' in low: add(i, cfg['tile_wall'])
    elif 'niche' in low: add(i, cfg['niche'])
    elif 'shower bench' in low: add(i, cfg['bench'])
    elif 'shower mud bed' in low: add(i, round(cfg['floor'] * 0.25, 1))
    elif 'lvp material' in low: add(i, round(cfg['floor'] * 1.05, 1))
    elif 'lvp labor' in low: add(i, round(cfg['floor'] * 1.05, 1))
    elif 'freestanding tub' in low and b == '1': add(i, 1)
    elif 'tub valve' in low and b == '1': add(i, 1)
    elif 'drop in tub' in low: continue

# shower glass
add(559, 1, 'master frameless'); add(557, 3, 'secondary baths framed')

print('ADDED %d lines' % len(ADD))
tot = 0.0
for i, qy, nt in ADD:
    l = L[i]
    tot += qy * float(l.get('unit_cost') or 0)
print('added direct cost: $%s' % format(round(tot), ','))
allm = matched + [[i, qy, nt] for i, qy, nt in ADD]
json.dump(allm, open('matched.json', 'w'), indent=1)
print('total lines now: %d' % len(allm))
