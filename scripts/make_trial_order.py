"""Fix the block split and trial order for every list (same for every participant).

Input:  outcomes/stimLists_outcomes.csv (from outcomes/assign_outcomes.py), restricted
        to the trials in stimLists.csv (so check41, the practice trial, is dropped).
Output: trialLists.js (loaded by index.html) and trialLists.csv (for records).

Design
  * 2 blocks. Blocks are split by shape: both maps a list has for a shape are in
    the same block, so each block has 18 shapes x 2 maps = 36 main trials.
    The same shapes go in block 1 for every list and both hazards.
  * The split is stratified so each block has 9 3-band and 9 6-band shapes in
    both lists (and a 5/4 split of every color x lightness x bands cell), and
    among those splits the one is chosen that best matches number of hits
    and mean house risk across blocks, for list A and list B.
  * 4 check trials per list, 2 per block (1 blue + 1 red), placed roughly a
    third and two thirds of the way through the block (jittered).
  * Within each block the order is shuffled once, with no two maps of the same
    shape back-to-back. Order depends only on the list (A/B), so flood_A and
    wildfire_A have the same trial sequence (just different hazard images).

Run from the repo root:  python3 scripts/make_trial_order.py
"""

import csv
import json
import random
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED = 20261107
N_SEARCH = 20000

with open(ROOT / "stimLists.csv") as f:
    in_lists = {r["stimulus"]: r for r in csv.DictReader(f)}
with open(ROOT / "outcomes" / "stimLists_outcomes.csv") as f:
    rows = [r for r in csv.DictReader(f) if r["stimulus"] in in_lists]
assert len(rows) == len(in_lists), "stimLists_outcomes.csv is missing trials from stimLists.csv"
for r in rows:
    assert r["list"] == in_lists[r["stimulus"]]["list"], r["stimulus"]
    r["shape"], r["bands"], r["outcome"] = int(r["shape"]), int(r["bands"]), int(r["outcome"])
    r["house_risk"] = float(r["house_risk"]) if r["house_risk"] else None

HAZARDS = sorted({r["hazard"] for r in rows})
LISTS = sorted({r["list"] for r in rows})
by_key = defaultdict(list)  # (hazard, list) -> rows
for r in rows:
    by_key[(r["hazard"], r["list"])].append(r)

# Outcomes and maps are the same across hazards (only the folder differs), so plan on one hazard.
ref = HAZARDS[0]
def strip(path):
    return path.split("/", 2)[2]
for h in HAZARDS:
    for l in LISTS:
        a = sorted((strip(r["stimulus"]), r["outcome"]) for r in by_key[(h, l)])
        b = sorted((strip(r["stimulus"]), r["outcome"]) for r in by_key[(ref, l)])
        assert a == b, f"{h}_{l} differs from {ref}_{l}"

main = {l: [r for r in by_key[(ref, l)] if r["trial_type"] == "shape"] for l in LISTS}
checks = {l: [r for r in by_key[(ref, l)] if r["trial_type"] == "check"] for l in LISTS}
shapes = sorted({r["shape"] for r in main[LISTS[0]]})
assert len(shapes) % 2 == 0

# Stratum of a shape = (lightness of its blue map in list A, bands of its maps in list A).
def shape_maps(l, n):
    return [r for r in main[l] if r["shape"] == n]

def stratum(n):
    a = shape_maps(LISTS[0], n)
    blue = [r for r in a if r["color"] == "blue"][0]
    return (blue["lightness"], blue["bands"])

strata = defaultdict(list)
for n in shapes:
    strata[stratum(n)].append(n)

# How many shapes of each stratum go to block 1: half. Strata are odd-sized (9), so the extra
# shape goes to (dark, 3) and (light, 6), keeping 9 3-band / 9 6-band shapes per block.
quota = {}
for (lay, b), members in strata.items():
    quota[(lay, b)] = len(members) // 2 + (len(members) % 2) * ((lay == "dark") == (b == 3))
assert sum(quota.values()) == len(shapes) // 2

def block_stats(l, block1):
    out = []
    for blk in (block1, set(shapes) - block1):
        rs = [r for r in main[l] if r["shape"] in blk]
        out.append((sum(r["outcome"] for r in rs), sum(r["house_risk"] for r in rs) / len(rs)))
    return out

def cost(block1):
    c = 0.0
    for l in LISTS:
        (h1, r1), (h2, r2) = block_stats(l, block1)
        c += (h1 - h2) ** 2 + ((r1 - r2) / 2.0) ** 2
    return c

rng = random.Random(SEED)
best, best_cost = None, float("inf")
for _ in range(N_SEARCH):
    b1 = set()
    for k, members in strata.items():
        b1.update(rng.sample(members, quota[k]))
    c = cost(b1)
    if c < best_cost:
        best, best_cost = b1, c
block_of_shape = {n: (1 if n in best else 2) for n in shapes}

# Checks: one blue and one red per block (colors are fixed per check number within a list).
check_nums = sorted({r["shape"] for r in checks[LISTS[0]]})
assert len(check_nums) == 4
col_a = {r["shape"]: r["color"] for r in checks[LISTS[0]]}
blues = [n for n in check_nums if col_a[n] == "blue"]
reds = [n for n in check_nums if col_a[n] == "red"]
assert len(blues) == len(reds) == 2
rng.shuffle(blues); rng.shuffle(reds)
block_of_check = {blues[0]: 1, reds[0]: 1, blues[1]: 2, reds[1]: 2}

def order_block(l, blk):
    """Shuffled main trials with 2 checks inserted ~1/3 and ~2/3 of the way through."""
    trials = [r for r in main[l] if block_of_shape[r["shape"]] == blk]
    while True:
        rng.shuffle(trials)
        if all(a["shape"] != b["shape"] for a, b in zip(trials, trials[1:])):
            break
    chk = [r for r in checks[l] if block_of_check[r["shape"]] == blk]
    rng.shuffle(chk)
    n = len(trials)
    pos = [round(n / 3) + rng.randint(-2, 2), round(2 * n / 3) + rng.randint(-2, 2)]
    seq = list(trials)
    for p, c in sorted(zip(pos, chk), key=lambda x: -x[0]):  # insert from the back
        seq.insert(p, c)
    return seq

order = {}  # list -> [(block, filename-without-hazard)]
for l in LISTS:
    seq = []
    for blk in (1, 2):
        seq += [(blk, strip(r["stimulus"])) for r in order_block(l, blk)]
    order[l] = seq

# Build the output for every hazard from the reference order.
trial_lists, out_rows = {}, []
for h in HAZARDS:
    for l in LISTS:
        lookup = {strip(r["stimulus"]): r for r in by_key[(h, l)]}
        entries, pos_in_block = [], Counter()
        for i, (blk, fn) in enumerate(order[l], start=1):
            r = lookup[fn]
            pos_in_block[blk] += 1
            e = dict(stimulus=r["stimulus"], hazard=h, list=l, trial_type=r["trial_type"],
                     shape=r["shape"], color=r["color"], lightness=r["lightness"], bands=r["bands"],
                     house_risk=r["house_risk"], outcome=r["outcome"],
                     block=blk, trial_in_block=pos_in_block[blk], trial_num=i)
            entries.append(e)
            out_rows.append(e)
        trial_lists[f"{h}_{l}"] = entries

# ---- checks ----
for key, entries in trial_lists.items():
    assert len(entries) == len(by_key[tuple(key.split("_"))])
    for blk in (1, 2):
        b = [e for e in entries if e["block"] == blk]
        m = [e for e in b if e["trial_type"] == "shape"]
        c = [e for e in b if e["trial_type"] == "check"]
        assert len(m) == len(shapes) and len(c) == 2 and {e["color"] for e in c} == {"blue", "red"}
        assert all(v == 2 for v in Counter(e["shape"] for e in m).values())
        assert Counter(e["bands"] for e in m) == {3: len(shapes) // 2, 6: len(shapes) // 2}
        assert b[0]["trial_type"] == "shape" and b[-1]["trial_type"] == "shape"
        cpos = [e["trial_in_block"] for e in c]
        print(f"{key} block {blk}: {len(m)} main + checks at {cpos} | "
              f"hits {sum(e['outcome'] for e in m)} | mean risk {sum(e['house_risk'] for e in m) / len(m):.1f} | "
              f"color {dict(Counter(e['color'] for e in m))} lightness {dict(Counter(e['lightness'] for e in m))}")
print("block 1 shapes:", sorted(best), "| block 1 checks:", sorted(n for n, b in block_of_check.items() if b == 1))

(ROOT / "trialLists.js").write_text(
    "// Generated by scripts/make_trial_order.py - do not edit by hand.\n"
    "// Fixed trial order per list (same for every participant). outcome: 1 = hazard reaches the house.\n"
    "var trialLists = " + json.dumps(trial_lists, indent=2) + ";\n"
)
with open(ROOT / "trialLists.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
    w.writeheader()
    w.writerows(out_rows)
print("Wrote trialLists.js and trialLists.csv")
