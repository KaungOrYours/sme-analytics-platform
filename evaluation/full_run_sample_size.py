"""
Experiment 4: sample-size sensitivity -- the other half of
docs/evaluation_protocol.md Section 7's "conditional expansion if time and
results allow" clause (the first half, corruption family, was exercised as
Experiments 2-3 in full_run_extended.py). Tests whether n/p's and sigma_cv's
discrimination ability (the RQ2/RQ3 question) changes when the automated
pipeline has less training data to work with -- directly on-topic for a
dissertation about small SME datasets, and the dimension CLAUDE.md's rigor
table explicitly asked for ("predefined sample-size levels, repeated at
multiple random seeds").

Design: the OUTER TEST SET IS NEVER SUBSAMPLED. Only the training partition
is reduced, to a fixed 50% (stratified, seeded), after the normal outer
split -- this isolates "less data to train on" from "less data to evaluate
on", keeping S_test estimates just as stable as Experiment 1's. Clean
condition only (no corruption combined with sample-size reduction, to keep
this a single-factor test, not a 2-factor design the project doesn't have
time to interpret).

Safety floor, checked before running (see evaluation/results/ README or the
2026-10-20 check in chat history): verified by direct inspection that every
one of the 7 datasets' minority class still has >= 8 training examples after
a 50% stratified subsample, comfortably above the 5-fold CV minimum
cv_scores_for_model requires. A runtime guard still skips (and logs why,
rather than crashing) any dataset/seed combination that would produce a
minority class below 5 after subsampling, in case a different seed's split
behaves worse than seed 1's check above.

Usage: python -m evaluation.full_run_sample_size development
       python -m evaluation.full_run_sample_size final-evaluation
"""
import json
import sys
import time
from pathlib import Path

from pmlb import fetch_data
from sklearn.model_selection import train_test_split

from evaluation.diagnostics import run_automated, run_manual_baseline, split_outer

RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

SEEDS = [1, 2, 3]
TRAIN_FRACTION = 0.5
MIN_CLASS_FLOOR = 5

GROUPS = {
    "development": ["molecular_biology_promoters", "appendicitis", "biomed", "irish"],
    "final-evaluation": ["labor", "mux6", "bupa"],
}
BIOMED_DROP_COLUMNS = [
    "Observation_number", "Hospital_identification_number_for_blood_sample", "Date_that_blood_sample_was_taken"
]


def load_dataset(name):
    df = fetch_data(name)
    if name == "biomed":
        df = df.drop(columns=BIOMED_DROP_COLUMNS)
    return df


def run_one(name, df, seed):
    start = time.time()
    X_train, X_test, y_train, y_test = split_outer(df, "target", seed)

    min_class = y_train.value_counts().min()
    if int(min_class * TRAIN_FRACTION) < MIN_CLASS_FLOOR:
        return {
            "dataset": name, "seed": seed, "skipped": True,
            "reason": f"minority class ({min_class}) would drop below the {MIN_CLASS_FLOOR}-example "
                      f"floor after a {TRAIN_FRACTION:.0%} subsample",
        }

    X_train_half, _, y_train_half, _ = train_test_split(
        X_train, y_train, train_size=TRAIN_FRACTION, random_state=seed, stratify=y_train
    )
    X_train_half = X_train_half.reset_index(drop=True)
    y_train_half = y_train_half.reset_index(drop=True)

    automated_full = run_automated(X_train, y_train, X_test, y_test, seed)
    automated_half = run_automated(X_train_half, y_train_half, X_test, y_test, seed)
    manual_full = run_manual_baseline(X_train, y_train, X_test, y_test, seed)
    manual_half = run_manual_baseline(X_train_half, y_train_half, X_test, y_test, seed)
    elapsed = time.time() - start

    return {
        "dataset": name, "seed": seed, "skipped": False,
        "elapsed_seconds": round(elapsed, 2),
        "full_size": {"automated": automated_full, "manual": manual_full},
        "half_size": {"automated": automated_half, "manual": manual_half},
    }


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in GROUPS:
        print(f"Usage: python -m evaluation.full_run_sample_size {{{'|'.join(GROUPS)}}}")
        sys.exit(1)
    group = sys.argv[1]
    datasets = GROUPS[group]

    results = []
    for name in datasets:
        print(f"Loading {name}...")
        df = load_dataset(name)
        for seed in SEEDS:
            r = run_one(name, df, seed)
            results.append(r)
            if r["skipped"]:
                print(f"  {name:30s} seed={seed} SKIPPED: {r['reason']}")
                continue
            fa, ha = r["full_size"]["automated"], r["half_size"]["automated"]
            print(
                f"  {name:30s} seed={seed} "
                f"| full n={fa['n']} n/p={fa['n']}/{fa['p']} sigma_cv={fa['sigma_cv']:.4f} G={fa['G']:+.4f} S_test={fa['s_test']:.4f} "
                f"| half n={ha['n']} n/p={ha['n']}/{ha['p']} sigma_cv={ha['sigma_cv']:.4f} G={ha['G']:+.4f} S_test={ha['s_test']:.4f} "
                f"| {r['elapsed_seconds']}s"
            )

    out_path = RESULTS_DIR / f"{group.replace('-', '_')}_sample_size_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    n_run = sum(1 for r in results if not r["skipped"])
    n_skipped = sum(1 for r in results if r["skipped"])
    print(f"\nWrote {len(results)} rows ({n_run} run, {n_skipped} skipped) to {out_path}")


if __name__ == "__main__":
    main()
