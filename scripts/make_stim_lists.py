"""Split the map stimuli into 4 lists (flood A/B, wildfire A/B).

Stimuli on disk (identical filenames for flood and wildfire):
  * shape01-36: 4 maps per shape. For each band count (specificity) there is
    one blue and one red map, and the two have opposite lightness, e.g.
    shape01 = blue dark/3 + red light/3, and blue light/6 + red dark/6.
  * check37-41: 2 maps per check shape (one blue, one red). check41 is the
    practice trial, so only check37-40 go into the lists.
  * example42/43: instruction examples only - not put in any list.

Design (same for flood and wildfire, so list A/B are matched across hazards):
  * Main shapes: each list gets one blue/red pair per shape that shares
    specificity (same bands, opposite lightness); list B gets the other pair,
    so A and B never share an image. Bands are assigned so each list has
    18 3-band / 18 6-band shapes, balanced over the two shape layouts
    (blue dark when 3-band vs blue light when 3-band), which also balances
    lightness x color x bands.
    -> 72 maps per list: 36 light / 36 dark, 36 3-band / 36 6-band,
       36 blue / 36 red, and 18 maps in each lightness x color cell.
  * Check shapes: 1 map per check shape per list (4 check trials); list B gets
    the other map of the pair. Colors alternate in list A (blue, red, ...).

Run from the repo root:  python3 scripts/make_stim_lists.py
Writes stimLists.js (loaded by index.html) and stimLists.csv (for records).
"""

import csv
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED = 20261106
HAZARDS = ["flood", "wildfire"]
SHAPES = range(1, 37)
CHECKS = range(37, 41)  # check41 = practice trial (index.html), not in the lists
PAT = re.compile(r"^(shape|check)(\d+)_(blues|reds)_(light|dark)_(3|6)bands\.png$")


def scan(hazard):
    """Return {(kind, num): [(color, light, bands), ...]} for files on disk."""
    found = defaultdict(list)
    for p in sorted((ROOT / "stimuli" / hazard).glob("*.png")):
        m = PAT.match(p.name)
        if m:
            kind, num, color, light, bands = m.groups()
            found[(kind, int(num))].append((color, light, int(bands)))
    return found


files = {h: scan(h) for h in HAZARDS}
assert files["flood"] == files["wildfire"], "flood and wildfire stimuli differ"
found = files["flood"]


def pair(kind, num, bands):
    """The (blue, red) maps of a shape at one band count (specificity)."""
    maps = [m for m in found[(kind, num)] if m[2] == bands]
    blue = [m for m in maps if m[0] == "blues"]
    red = [m for m in maps if m[0] == "reds"]
    assert len(blue) == 1 and len(red) == 1 and blue[0][1] != red[0][1], (kind, num, bands, maps)
    return [blue[0], red[0]]


def layout(num):
    """Lightness of the blue 3-band map - distinguishes the two shape layouts."""
    return pair("shape", num, 3)[0][1]


for n in SHAPES:
    assert len(found[("shape", n)]) == 4, (n, found[("shape", n)])
    pair("shape", n, 6)
for n in CHECKS:
    assert len(found[("check", n)]) == 2, (n, found[("check", n)])

rng = random.Random(SEED)

# List A band count per main shape: half 3-band / half 6-band within each layout.
bands_a = {}
for lay in ("light", "dark"):
    group = [n for n in SHAPES if layout(n) == lay]
    assert len(group) % 2 == 0
    bands = [3, 6] * (len(group) // 2)
    rng.shuffle(bands)
    bands_a.update(zip(group, bands))

# List A check maps: alternate blue / red.
check_color_a = {n: ("blues" if i % 2 == 0 else "reds") for i, n in enumerate(CHECKS)}


def other(x, a, b):
    return b if x == a else a


def build_list(which):
    items = []
    for n in SHAPES:
        b = bands_a[n] if which == "A" else other(bands_a[n], 3, 6)
        for color, lt, bands in pair("shape", n, b):
            items.append(dict(kind="shape", shape=n, color=color, lightness=lt, bands=bands))
    for n in CHECKS:
        color = check_color_a[n] if which == "A" else other(check_color_a[n], "blues", "reds")
        (m,) = [m for m in found[("check", n)] if m[0] == color]
        items.append(dict(kind="check", shape=n, color=m[0], lightness=m[1], bands=m[2]))
    return items


lists = {}
rows = []
for hazard in HAZARDS:
    for which in ["A", "B"]:
        key = f"{hazard}_{which}"
        entries = []
        for it in build_list(which):
            path = f"stimuli/{hazard}/{it['kind']}{it['shape']:02d}_{it['color']}_{it['lightness']}_{it['bands']}bands.png"
            assert (ROOT / path).exists(), path
            entry = dict(stimulus=path, hazard=hazard, list=which, trial_type=it["kind"],
                         shape=it["shape"], color=it["color"].rstrip("s"),
                         lightness=it["lightness"], bands=it["bands"])
            entries.append(entry)
            rows.append(entry)
        lists[key] = entries

# ---- checks ----
for key, entries in lists.items():
    main = [e for e in entries if e["trial_type"] == "shape"]
    chk = [e for e in entries if e["trial_type"] == "check"]
    assert len(main) == 2 * len(SHAPES) and len(chk) == len(CHECKS)
    per_shape = Counter((e["shape"], e["color"]) for e in main)
    assert all(v == 1 for v in per_shape.values()) and len(per_shape) == 2 * len(SHAPES)
    for fields in (("lightness",), ("bands",), ("color",), ("lightness", "color", "bands")):
        c = Counter(tuple(e[f] for f in fields) for e in main)
        assert len(set(c.values())) == 1, (key, fields, c)
    print(key, "main:", dict(Counter((e["lightness"], e["color"], e["bands"]) for e in main)),
          "| checks:", [(e["shape"], e["color"], e["lightness"], e["bands"]) for e in chk])
for h in HAZARDS:
    a = {e["stimulus"] for e in lists[f"{h}_A"]}
    b = {e["stimulus"] for e in lists[f"{h}_B"]}
    assert not a & b
    on_disk = {f"stimuli/{h}/{p.name}" for p in (ROOT / "stimuli" / h).glob("*.png")
               if PAT.match(p.name) and not p.name.startswith("check41")}
    assert a | b == on_disk, on_disk - (a | b)

(ROOT / "stimLists.js").write_text(
    "// Generated by scripts/make_stim_lists.py - do not edit by hand.\n"
    "var stimLists = " + json.dumps(lists, indent=2) + ";\n"
)
with open(ROOT / "stimLists.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
print("Wrote stimLists.js and stimLists.csv")
