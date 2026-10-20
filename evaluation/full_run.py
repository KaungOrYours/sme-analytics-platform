"""
Full-protocol run (docs/evaluation_protocol.md Section 12, steps 1-2): the
actual RQ1/RQ2 (development group) and RQ3 (final-evaluation group) data
collection, as opposed to pilot.py's exploratory pilot.

Grid per group: {clean, 15%, 35%} missing-value rates x {seed 1, 2, 3} x
{automated, manual baseline} pipelines, run on each dataset in the group.
For 4 development datasets that is 4 x 3 x 3 x 2 = 72 pipeline-runs; for the
3 final-evaluation datasets, 3 x 3 x 3 x 2 = 54.

RQ2 scope clarification (not specified explicitly in the frozen protocol,
decided here and recorded in docs/evaluation_protocol.md): the diagnostics
(n/p, sigma_CV) are scored for RQ2 on AUTOMATED-pipeline runs only, since
RQ2 and the dissertation's novelty claim are specifically about whether the
automated pipeline's own signals predict its own failures -- not a pooled
automated+manual sample. The manual baseline's G/sigma_CV are still
recorded (every run computes both), just not used in the RQ2 diagnostic
scoring in score_rq2.py. RQ1 (the automated-vs-manual comparison) uses
both pipelines' S_test on the same conditions, as already implemented.

Usage: python -m evaluation.full_run development
       python -m evaluation.full_run final-evaluation
"""
import json
import sys
import time
from pathlib import Path

from pmlb import fetch_data

from evaluation.diagnostics import run_automated, run_manual_baseline, split_outer
from evaluation.injectors import inject_missing_values

RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

SEEDS = [1, 2, 3]
MISSING_RATES = [0.0, 0.15, 0.35]  # 0.0 = clean condition

# Per docs/datasets.md's locked development/final-evaluation split.
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


def run_one(name, df, seed, missing_rate):
    start = time.time()
    X_train, X_test, y_train, y_test = split_outer(df, "target", seed)

    if missing_rate > 0:
        train_df = X_train.copy()
        train_df["target"] = y_train
        corrupted, _ = inject_missing_values(train_df, missing_rate, seed, columns=list(X_train.columns))
        X_train = corrupted.drop(columns=["target"])

    automated = run_automated(X_train, y_train, X_test, y_test, seed)
    manual = run_manual_baseline(X_train, y_train, X_test, y_test, seed)
    elapsed = time.time() - start

    return {
        "dataset": name, "seed": seed, "missing_rate": missing_rate,
        "elapsed_seconds": round(elapsed, 2),
        "automated": automated, "manual": manual,
    }


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in GROUPS:
        print(f"Usage: python -m evaluation.full_run {{{'|'.join(GROUPS)}}}")
        sys.exit(1)
    group = sys.argv[1]
    datasets = GROUPS[group]

    results = []
    for name in datasets:
        print(f"Loading {name}...")
        df = load_dataset(name)
        for missing_rate in MISSING_RATES:
            for seed in SEEDS:
                r = run_one(name, df, seed, missing_rate)
                results.append(r)
                print(
                    f"  {name:30s} rate={missing_rate:.2f} seed={seed} "
                    f"| auto n/p={r['automated']['n']}/{r['automated']['p']} "
                    f"sigma_cv={r['automated']['sigma_cv']:.4f} G={r['automated']['G']:+.4f} "
                    f"| manual G={r['manual']['G']:+.4f} "
                    f"| {r['elapsed_seconds']}s"
                )

    out_path = RESULTS_DIR / f"{group.replace('-', '_')}_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nWrote {len(results)} runs ({len(datasets)} datasets x {len(MISSING_RATES)} rates x "
          f"{len(SEEDS)} seeds x 2 pipelines) to {out_path}")

    total_time = sum(r["elapsed_seconds"] for r in results)
    print(f"Total wall-clock time: {total_time:.1f}s across {len(results)} runs "
          f"({total_time/len(results):.3f}s/run average)")


if __name__ == "__main__":
    main()
