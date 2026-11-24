"""POST-HOC: is the across-group instability of a frozen threshold distinguishable
from random partitioning of the same datasets?

THIS IS POST-HOC. Not pre-registered. It re-measures stored runs and adds none.

Why it exists
-------------
Studies 1-3 reported that a frozen cut behaves very differently on Groups A, B and
C -- firing rates of 16.3%, 44.4% and 38.1%, and an MCC running from -0.185 to
+0.262 -- and read that as evidence that the threshold does not transfer.

Groups A, B and C are disjoint subsets of the SAME 25 datasets. So before that
spread can mean anything, it has to be compared against the spread a RANDOM 7/9/9
partition of those same 25 datasets would produce. Nobody computed that null. This
module does.

The null is constructed by permuting dataset labels, not runs: each draw assigns
the 25 datasets at random to blocks of 7, 9 and 9, carries every one of a
dataset's 21 runs with it, and re-scores the frozen rule in each block exactly as
the original analysis did. That preserves every within-dataset property and
destroys only the particular assignment of datasets to groups, which is the thing
under test.

Two statistics, matching what was reported:
  - firing-rate spread  max - min of the proportion of runs the rule fires on
  - MCC spread          max - min of the binary MCC against poor_optimism

If the observed spreads sit inside this null, then "the threshold does not
transfer" and "we have 25 dataset clusters" are the same observation, and only the
second is supportable.

One caveat that makes the null CONSERVATIVE, i.e. favourable to the original
claim, and which must be stated wherever this is reported: Group A was not a
random draw. Its datasets were deliberately chosen to span n/p from 1.86 to 100,
so the real partition was selected to maximise predictor range in a way the null
does not model. The true p-value is therefore larger than the one reported here.

Reads only. Writes results/partition_null_scores.json.

Run from the REPO ROOT:
    backend/venv/bin/python3 -m evaluation.score_partition_null
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from evaluation.recalibrate_study3 import DIAGNOSTIC_SPECS
from evaluation.score_rq2 import confusion, mcc

RESULTS_DIR = Path(__file__).resolve().parent / "results"
OUTPUT_FILE = "partition_null_scores.json"

GROUP_FILES = {
    "A": "study2_group_A_results.json",
    "B": "study2_group_B_results.json",
    "C": "study2_group_C_results.json",
}
LABEL = "poor_optimism"

N_PERMUTATIONS = 5000
PERMUTATION_SEED = 0

# The real partition's block sizes. Held fixed so the null differs from the
# observation only in WHICH datasets land in which block.
BLOCK_SIZES = (7, 9, 9)


def load_by_dataset():
    """{dataset: [run, ...]} over all three groups, plus the true group of each."""
    by_dataset, true_group = {}, {}
    for group, filename in GROUP_FILES.items():
        path = RESULTS_DIR / filename
        if not path.exists():
            raise SystemExit(f"{path} not found.")
        with path.open() as fh:
            payload = json.load(fh)
        for record in payload["runs"]:
            a = record.get("automated")
            if not a:
                continue
            name = record["dataset"]
            # recalibrate_study3.load_runs synthesises n_over_p; the raw stored
            # record carries only n and p. Without this the n/p spec silently
            # scores None on every run, every draw is discarded, and the result
            # reads as "not estimable" when it is simply absent. That defect put
            # a claim quantified over six diagnostics into an earlier draft when
            # only five had been tested.
            a = dict(a, n_over_p=(a["n"] / a["p"]) if a.get("p") else None)
            by_dataset.setdefault(name, []).append(a)
            true_group[name] = group
    return by_dataset, true_group


NON_STRICT_AT_ANCHOR = {"evalml_range"}


def score_block(datasets, by_dataset, spec, diag_name=None):
    """Firing rate and MCC for the frozen anchor over one block of datasets."""
    name_is_non_strict = diag_name in NON_STRICT_AT_ANCHOR
    trig, poor = [], []
    for name in datasets:
        for a in by_dataset[name]:
            value = a.get(spec["key"])
            if value is None:
                continue
            # evalml_range's frozen rule is non-strict; see NON_STRICT_AT_ANCHOR
            # in score_clustered_intervals.py for why the generic comparator is
            # wrong for it at the anchor.
            if spec["direction"] > 0:
                fired = value >= spec["anchor"] if name_is_non_strict else value > spec["anchor"]
            else:
                fired = value < spec["anchor"]
            trig.append(bool(fired))
            poor.append(bool(a["labels"][LABEL]))
    if not trig:
        return None, None
    firing_rate = sum(trig) / len(trig)
    if len(set(poor)) < 2:
        return firing_rate, None
    return firing_rate, mcc(*confusion(trig, poor))


def spreads(blocks, by_dataset, spec, diag_name=None):
    rates, mccs = [], []
    for block in blocks:
        rate, value = score_block(block, by_dataset, spec, diag_name)
        if rate is not None:
            rates.append(rate)
        if value is not None:
            mccs.append(value)
    return (
        max(rates) - min(rates) if len(rates) == len(blocks) else None,
        max(mccs) - min(mccs) if len(mccs) == len(blocks) else None,
    )


def permutation_null(by_dataset, true_blocks, spec, diag_name=None, n=N_PERMUTATIONS, seed=PERMUTATION_SEED):
    observed_rate, observed_mcc = spreads(true_blocks, by_dataset, spec, diag_name)
    names = sorted(by_dataset)
    rng = random.Random(seed)

    rate_draws, mcc_draws, undefined = [], [], 0
    for _ in range(n):
        shuffled = names[:]
        rng.shuffle(shuffled)
        blocks, start = [], 0
        for size in BLOCK_SIZES:
            blocks.append(shuffled[start:start + size])
            start += size
        rate, value = spreads(blocks, by_dataset, spec, diag_name)
        if rate is None or value is None:
            undefined += 1
            continue
        rate_draws.append(rate)
        mcc_draws.append(value)

    def summarise(observed, draws):
        if observed is None or not draws:
            return {"observed": observed, "p_value": None, "n_draws": len(draws)}
        ordered = sorted(draws)
        at_least = sum(1 for v in draws if v >= observed)
        return {
            "observed": observed,
            "null_median": ordered[len(ordered) // 2],
            "null_p95": ordered[int(0.95 * len(ordered))],
            "p_value": at_least / len(draws),
            "n_draws": len(draws),
        }

    return {
        "firing_rate_spread": summarise(observed_rate, rate_draws),
        "mcc_spread": summarise(observed_mcc, mcc_draws),
        "n_undefined_draws": undefined,
    }


def main():
    by_dataset, true_group = load_by_dataset()
    true_blocks = [
        sorted(n for n, g in true_group.items() if g == group) for group in ("A", "B", "C")
    ]
    assert [len(b) for b in true_blocks] == list(BLOCK_SIZES), [len(b) for b in true_blocks]

    result = {
        "analysis": "random-partition null for across-group threshold instability (POST-HOC)",
        "post_hoc": True,
        "pre_registered": False,
        "label": LABEL,
        "n_datasets": len(by_dataset),
        "block_sizes": list(BLOCK_SIZES),
        "n_permutations": N_PERMUTATIONS,
        "permutation_seed": PERMUTATION_SEED,
        "conservative_caveat": (
            "Group A's datasets were deliberately chosen to span n/p from 1.86 to "
            "100, so the real partition was selected to maximise predictor range in "
            "a way this null does not model. The true p-value is larger than the "
            "one reported."
        ),
        "diagnostics": {},
    }

    print()
    print(f"RANDOM-PARTITION NULL -- {N_PERMUTATIONS} draws of a "
          f"{'/'.join(map(str, BLOCK_SIZES))} split of the same {len(by_dataset)} datasets")
    print("  (permuting dataset labels; every run travels with its dataset)")
    print()
    print(f"  {'diagnostic':<20} {'statistic':<20} {'observed':>9} {'null med':>9} "
          f"{'null p95':>9} {'p':>7}")
    for name, spec in DIAGNOSTIC_SPECS.items():
        block = permutation_null(by_dataset, true_blocks, spec, diag_name=name)
        result["diagnostics"][name] = block
        for key, label in (("firing_rate_spread", "firing-rate spread"),
                           ("mcc_spread", "MCC spread")):
            s = block[key]
            if s.get("p_value") is None:
                print(f"  {name:<20} {label:<20} {'not estimable':>9}")
                continue
            flag = "" if s["p_value"] < 0.05 else "   <- not distinguishable"
            print(f"  {name:<20} {label:<20} {s['observed']:>9.3f} "
                  f"{s['null_median']:>9.3f} {s['null_p95']:>9.3f} "
                  f"{s['p_value']:>7.3f}{flag}")
        print()

    print("  A spread that the null reproduces is evidence about cluster count, not")
    print("  about threshold transfer. See conservative_caveat in the output file.")
    print()

    out = RESULTS_DIR / OUTPUT_FILE
    with out.open("w") as fh:
        json.dump(result, fh, indent=2)
    print(f"Written: {out}")


if __name__ == "__main__":
    main()
