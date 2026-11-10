"""Fix the block split and trial order for each condition (same for every participant).

There are 2 conditions: flood and wildfire. Each condition shows ALL maps of its hazard,
i.e. the former lists A and B combined (stimLists.csv still records which half - A or B -
each map came from; that label is kept as `stim_set`).

Input:  outcomes/stimLists_outcomes.csv (from outcomes/assign_outcomes.py), restricted
        to the trials in stimLists.csv (so check41, the practice trial, is dropped).
Output: trialLists.js (loaded by index.html) and trialLists.csv (for records).

Design
  * 144 main trials (36 shapes x 4 maps) + 8 check trials (check37-40 x blue/red).
  * 2 blocks. Blocks are split by shape: all 4 maps of a shape are in the same block,
    so each block has 18 shapes x 4 maps = 72 main trials. The same shapes go in
    block 1 for both hazards.
  * The split is stratified (9 shapes of each shape layout per block, which balances
    every color x lightness x bands cell), and among those splits the one is chosen
    that best matches number of hits and mean house risk across blocks.
  * 4 check trials per block: each check shape once per block, 2 blue + 2 red per block
    (the other color of each check shape is in the other block), placed roughly 1/5,
    2/5, 3/5 and 4/5 of the way through the block (jittered).
  * Within each block the order is shuffled once, with no two maps of the same shape
    back-to-back. flood and wildfire have the same trial sequence (just different
    hazard images).

Run from the repo root:  python3 scripts/make_trial_order.py
"""

import csv
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED = 20261110
N_SEARCH = 20000
N_CHECKS_PER_BLOCK = 4

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
by_hazard = defaultdict(list)  # hazard -> rows (former lists A and B combined)
for r in rows:
    by_hazard[r["hazard"]].append(r)

# Outcomes and maps are the same across hazards (only the folder differs), so plan on one hazard.
ref = HAZARDS[0]
def strip(path):
    return path.split("/", 2)[2]
for h in HAZARDS:
    a = sorted((strip(r["stimulus"]), r["outcome"]) for r in by_hazard[h])
    b = sorted((strip(r["stimulus"]), r["outcome"]) for r in by_hazard[ref])
    assert a == b, f"{h} differs from {ref}"

main = [r for r in by_hazard[ref] if r["trial_type"] == "shape"]
checks = [r for r in by_hazard[ref] if r["trial_type"] == "check"]
shapes = sorted({r["shape"] for r in main})
assert len(shapes) % 2 == 0
assert all(v == 4 for v in Counter(r["shape"] for r in main).values())

# Layout of a shape = lightness of its blue 3-band map (the two layouts have opposite
# lightness in every color x bands cell, so taking half of each layout balances all cells).
def layout(n):
    (blue3,) = [r for r in main if r["shape"] == n and r["color"] == "blue" and r["bands"] == 3]
    return blue3["lightness"]

strata = defaultdict(list)
for n in shapes:
    strata[layout(n)].append(n)
quota = {k: len(v) // 2 for k, v in strata.items()}
assert all(len(v) % 2 == 0 for v in strata.values()) and sum(quota.values()) == len(shapes) // 2

def block_stats(block1):
    out = []
    for blk in (block1, set(shapes) - block1):
        rs = [r for r in main if r["shape"] in blk]
        out.append((sum(r["outcome"] for r in rs), sum(r["house_risk"] for r in rs) / len(rs)))
    return out

def cost(block1):
    (h1, r1), (h2, r2) = block_stats(block1)
    return (h1 - h2) ** 2 + ((r1 - r2) / 2.0) ** 2

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

# Checks: each check shape has a blue and a red map; one goes in each block, with
# 2 blue + 2 red per block.
check_nums = sorted({r["shape"] for r in checks})
assert len(check_nums) == N_CHECKS_PER_BLOCK and len(checks) == 2 * len(check_nums)
blue_block1 = set(rng.sample(check_nums, len(check_nums) // 2))
def check_block(r):
    blue_first = r["shape"] in blue_block1
    return 1 if (r["color"] == "blue") == blue_first else 2

def order_block(blk):
    """Shuffled main trials with the block's checks spread evenly through it."""
    trials = [r for r in main if block_of_shape[r["shape"]] == blk]
    while True:
        rng.shuffle(trials)
        if all(a["shape"] != b["shape"] for a, b in zip(trials, trials[1:])):
            break
    chk = [r for r in checks if check_block(r) == blk]
    rng.shuffle(chk)
    n, k = len(trials), len(chk)
    pos = [round((i + 1) * n / (k + 1)) + rng.randint(-2, 2) for i in range(k)]
    seq = list(trials)
    for p, c in sorted(zip(pos, chk), key=lambda x: -x[0]):  # insert from the back
        seq.insert(p, c)
    return seq

order = []  # [(block, filename-without-hazard)]
for blk in (1, 2):
    order += [(blk, strip(r["stimulus"])) for r in order_block(blk)]

# Build the output for every hazard from the reference order.
trial_lists, out_rows = {}, []
for h in HAZARDS:
    lookup = {strip(r["stimulus"]): r for r in by_hazard[h]}
    entries, pos_in_block = [], Counter()
    for i, (blk, fn) in enumerate(order, start=1):
        r = lookup[fn]
        pos_in_block[blk] += 1
        e = dict(stimulus=r["stimulus"], hazard=h, list=h, stim_set=r["list"],
                 trial_type=r["trial_type"], shape=r["shape"], color=r["color"],
                 lightness=r["lightness"], bands=r["bands"],
                 house_risk=r["house_risk"], outcome=r["outcome"],
                 block=blk, trial_in_block=pos_in_block[blk], trial_num=i)
        entries.append(e)
        out_rows.append(e)
    trial_lists[h] = entries

# ---- checks ----
for key, entries in trial_lists.items():
    assert len(entries) == len(by_hazard[key]) == len({e["stimulus"] for e in entries})
    for blk in (1, 2):
        b = [e for e in entries if e["block"] == blk]
        m = [e for e in b if e["trial_type"] == "shape"]
        c = [e for e in b if e["trial_type"] == "check"]
        assert len(m) == 2 * len(shapes) and len(c) == N_CHECKS_PER_BLOCK
        assert Counter(e["color"] for e in c) == {"blue": 2, "red": 2}
        assert len({e["shape"] for e in c}) == N_CHECKS_PER_BLOCK
        assert all(v == 4 for v in Counter(e["shape"] for e in m).values())
        cells = Counter((e["color"], e["lightness"], e["bands"]) for e in m)
        assert len(cells) == 8 and len(set(cells.values())) == 1, cells
        assert b[0]["trial_type"] == "shape" and b[-1]["trial_type"] == "shape"
        cpos = [e["trial_in_block"] for e in c]
        print(f"{key} block {blk}: {len(m)} main + checks at {cpos} | "
              f"hits {sum(e['outcome'] for e in m)} | mean risk {sum(e['house_risk'] for e in m) / len(m):.1f} | "
              f"A/B {dict(Counter(e['stim_set'] for e in m))}")
print("block 1 shapes:", sorted(best))

(ROOT / "trialLists.js").write_text(
    "// Generated by scripts/make_trial_order.py - do not edit by hand.\n"
    "// Fixed trial order per condition (same for every participant). outcome: 1 = hazard reaches the house.\n"
    "var trialLists = " + json.dumps(trial_lists, indent=2) + ";\n"
)
with open(ROOT / "trialLists.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
    w.writeheader()
    w.writerows(out_rows)
print("Wrote trialLists.js and trialLists.csv")
