"""
assign_outcomes.py
------------------
Assign a fixed outcome (hazard hits the house: 1 / does not: 0) to every
trial in each counterbalancing list, so realized outcome rates match the
"ground truth" risk shown on the maps.

Ground truth = each house's continuous risk (house_risk_continuous / 100).
The same house sits in different bands in 3- vs 6-band maps; its continuous
risk lies inside whichever band is shown, so outcomes are honest for every map.

Per list in stimLists.csv (72 main trials = 36 shapes x 2 showings), outcomes are chosen so that
the number of hits is as close as possible to the expected number, i.e. the
sum of p, within each of these groups:
    - the whole list                      (exact: round(sum p))
    - each of the 8 conditions            (9 trials each)
    - each 6-band risk bin (10-25 ... 85-100)
    - each factor level (color, lightness, specificity)
    - each shape (2 showings; lighter weight)
Check trials (house outside the hotspot) always get outcome 0.

Shapes are identical across concepts, so wildfire and flood get the SAME
outcomes within a list (keeps the concept comparison clean).

Every participant on a given list sees the same outcomes; only trial order varies.

Usage:
    python assign_outcomes.py stimLists.csv stimuli.csv
        -> stimLists_outcomes.csv and stimLists_outcomes.js (same structure as
           stimLists.js, plus house_risk and outcome on every trial)
"""

import argparse
import json
import numpy as np
import pandas as pd

RISK_BINS = [10, 25, 40, 55, 70, 85, 100.0001]
WEIGHTS = dict(condition=1.0, risk_bin=1.0, factor=1.0, shape=0.25)
N_ITER = 60000


def group_indices(df):
    """List of (weight, index-array) for every group to balance."""
    groups = []
    for col, w in [("condition_index", WEIGHTS["condition"]),
                   ("risk_bin", WEIGHTS["risk_bin"]),
                   ("color_scale", WEIGHTS["factor"]),
                   ("lightness", WEIGHTS["factor"]),
                   ("n_bands", WEIGHTS["factor"]),
                   ("shape_id", WEIGHTS["shape"])]:
        for _, idx in df.groupby(col).indices.items():
            groups.append((w, np.asarray(idx)))
    return groups


def loss(y, p, groups):
    return sum(w * (y[idx].sum() - p[idx].sum()) ** 2 for w, idx in groups)


def assign_list(df, rng):
    p = df["p"].to_numpy()
    n = len(p)
    n_hit = int(round(p.sum()))
    groups = group_indices(df)

    # start: systematic sampling over trials sorted by risk (higher p -> more hits)
    order = np.argsort(p, kind="stable")
    cum = np.cumsum(p[order]) + rng.uniform(0, 1)
    y = np.zeros(n, int)
    y[order] = np.diff(np.floor(np.concatenate([[cum[0] - p[order][0]], cum]))).astype(int).clip(0, 1)
    # fix total exactly
    while y.sum() > n_hit:
        on = np.flatnonzero(y == 1); y[on[np.argmin(p[on])]] = 0
    while y.sum() < n_hit:
        off = np.flatnonzero(y == 0); y[off[np.argmax(p[off])]] = 1

    # local search: swap one hit with one miss (total stays fixed); keep if not worse
    best = loss(y, p, groups)
    for _ in range(N_ITER):
        i = rng.choice(np.flatnonzero(y == 1))
        j = rng.choice(np.flatnonzero(y == 0))
        y[i], y[j] = 0, 1
        new = loss(y, p, groups)
        if new <= best:
            best = new
        else:
            y[i], y[j] = 1, 0
    return y, best


def report(df, list_id):
    print(f"\n=== list {list_id}: {len(df)} main trials, "
          f"{df.outcome.sum()} hits (expected {df.p.sum():.1f}) ===")
    for col in ["risk_bin", "condition_label", "color_scale", "lightness", "n_bands"]:
        t = df.groupby(col, observed=True).agg(n=("p", "size"), expected=("p", "sum"),
                                               hits=("outcome", "sum"))
        t["expected"] = t["expected"].round(2)
        print(f"\n-- by {col}\n{t.to_string()}")
    per_shape = df.groupby("shape_id").agg(p=("p", "first"), hits=("outcome", "sum"))
    print("\n-- shapes by hits out of 2 (mean risk of those shapes)")
    print(per_shape.groupby("hits").p.agg(["size", "mean"]).round(2).to_string())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stim_lists_csv", help="stimLists.csv (the fixed trial lists)")
    ap.add_argument("stimuli_csv", help="stimuli.csv from make_hazard_maps.py (house risks)")
    ap.add_argument("--out", default="stimLists_outcomes")
    ap.add_argument("--seed", type=int, default=2026)
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)

    lists = pd.read_csv(args.stim_lists_csv)
    stim = pd.read_csv(args.stimuli_csv)
    lists["_fn"] = lists["stimulus"].str.replace("stimuli/", "", n=1, regex=False)
    risk = stim.set_index("filename")["house_risk_continuous"]
    missing = ~lists["_fn"].isin(risk.index)
    if missing.any():
        raise SystemExit(f"{missing.sum()} stimuli not found in {args.stimuli_csv}, e.g. "
                         f"{lists.loc[missing, 'stimulus'].iloc[0]}")
    lists["house_risk"] = lists["_fn"].map(risk)
    lists["p"] = lists["house_risk"].fillna(0) / 100.0
    lists["risk_bin"] = pd.cut(lists["house_risk"], RISK_BINS, right=False)
    # columns the balancing code expects
    lists["condition_index"] = lists.color + "/" + lists.lightness + "/" + lists.bands.astype(str)
    lists["condition_label"] = lists["condition_index"]
    lists["color_scale"], lists["n_bands"], lists["shape_id"] = lists["color"], lists["bands"], lists["shape"]

    # the same shape has the same house in every hazard, so solve each list once
    # (using the first hazard) and copy the outcomes to the other hazards
    ref_hazard = lists.hazard.iloc[0]
    outcome = {}
    for list_id in sorted(lists.list.unique()):
        ref = lists[(lists.hazard == ref_hazard) & (lists.list == list_id)]
        main_trials = ref[ref.trial_type != "check"].reset_index()
        y, _ = assign_list(main_trials, rng)
        main_trials["outcome"] = y
        report(main_trials, list_id)
        for _, r in main_trials.iterrows():
            outcome[(list_id, r.stimulus.split("/")[-1])] = int(r.outcome)
        for _, r in ref[ref.trial_type == "check"].iterrows():
            outcome[(list_id, r.stimulus.split("/")[-1])] = 0
    lists["outcome"] = [outcome[(l, s.split("/")[-1])] for l, s in zip(lists.list, lists.stimulus)]

    # consistency checks
    for hz in lists.hazard.unique():
        a = lists[lists.hazard == hz].sort_values(["list", "shape", "stimulus"]).outcome.to_numpy()
        b = lists[lists.hazard == ref_hazard].sort_values(["list", "shape", "stimulus"]).outcome.to_numpy()
        assert (a == b).all(), "outcomes differ across hazards"
    assert (lists.loc[lists.trial_type == "check", "outcome"] == 0).all()

    keep = ["stimulus", "hazard", "list", "trial_type", "shape", "color",
            "lightness", "bands", "house_risk", "outcome"]
    out = lists[keep].copy()
    out["house_risk"] = out["house_risk"].round(1)
    out.to_csv(args.out + ".csv", index=False)

    js = {}
    for (hz, l), g in out.groupby(["hazard", "list"], sort=True):
        recs = g.drop(columns="house_risk").to_dict("records")
        for r, hr in zip(recs, g.house_risk):
            r["house_risk"] = None if pd.isna(hr) else float(hr)
            r["outcome"] = int(r["outcome"]); r["shape"] = int(r["shape"]); r["bands"] = int(r["bands"])
        js[f"{hz}_{l}"] = recs
    with open(args.out + ".js", "w") as f:
        f.write("// Generated by assign_outcomes.py - do not edit by hand.\n")
        f.write("// outcome: 1 = hazard reaches the house, 0 = it does not.\n")
        f.write("var stimLists = " + json.dumps(js, indent=2) + ";\n")

    print(f"\nwrote {args.out}.csv and {args.out}.js")
    print(out.groupby(["hazard", "list"]).agg(trials=("outcome", "size"),
                                              hits=("outcome", "sum")).to_string())


if __name__ == "__main__":
    main()
