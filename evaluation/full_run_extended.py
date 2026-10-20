"""
Extended-protocol run: Experiments 2-3 (docs/evaluation_protocol.md's
Section 7 "conditional, not committed" expansion clause, exercised
2026-10-20). `evaluation/full_run.py` (Experiment 1) is left untouched as
the frozen, committed single-corruption-family design -- this script is a
separate, clearly-labelled extension beyond that committed scope, not a
replacement for it.

Corruption families covered here: "duplicates" and "outliers" (from
evaluation/injectors.py's INJECTORS dict). "inconsistent_categories" is
deliberately excluded -- checked first (2026-10-20) and confirmed a
complete no-op on this project's dataset source: all 7 PMLBmini/TabMini
datasets are 100% numerically encoded (0 object-dtype columns across any
of them), and inject_inconsistent_categories only perturbs object-dtype
columns. Running it would silently reproduce the clean condition under a
different label. Documented here rather than run and discovered later.

Same grid shape as Experiment 1 otherwise: {15%, 35%} corruption rate
(0% is Experiment 1's own clean condition, not re-run here, to avoid
burning compute on an identical duplicate of already-frozen results) x
{seed 1, 2, 3} x {automated, manual baseline}, per dataset per group.

Usage: python -m evaluation.full_run_extended development duplicates
       python -m evaluation.full_run_extended final-evaluation outliers
"""
import json
import sys
import time
from pathlib import Path

from pmlb import fetch_data

from evaluation.diagnostics import run_automated, run_manual_baseline, split_outer
from evaluation.injectors import INJECTORS

RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

SEEDS = [1, 2, 3]
CORRUPTION_RATES = [0.15, 0.35]
SUPPORTED_CORRUPTIONS = ["duplicates", "outliers"]  # inconsistent_categories excluded, see module docstring

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


def run_one(name, df, seed, rate, corruption_type):
    start = time.time()
    X_train, X_test, y_train, y_test = split_outer(df, "target", seed)

    injector = INJECTORS[corruption_type]
    train_df = X_train.copy()
    train_df["target"] = y_train
    feature_cols = list(X_train.columns)
    if corruption_type == "duplicates":
        # inject_duplicates has no columns param -- it duplicates whole rows,
        # target included, which is correct (a duplicated row's label must
        # match its duplicated features).
        corrupted, _ = injector(train_df, rate, seed)
    else:
        # outliers/inconsistent_categories default to ALL matching-dtype
        # columns, which would include "target" (numeric) if not restricted
        # -- explicitly scope to feature columns only, same pattern
        # full_run.py already uses for inject_missing_values.
        corrupted, _ = injector(train_df, rate, seed, columns=feature_cols)
    X_train = corrupted.drop(columns=["target"])
    y_train = corrupted["target"]

    automated = run_automated(X_train, y_train, X_test, y_test, seed)
    manual = run_manual_baseline(X_train, y_train, X_test, y_test, seed)
    elapsed = time.time() - start

    return {
        "dataset": name, "seed": seed, "corruption_type": corruption_type, "rate": rate,
        "elapsed_seconds": round(elapsed, 2),
        "automated": automated, "manual": manual,
    }


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in GROUPS or sys.argv[2] not in SUPPORTED_CORRUPTIONS:
        print(f"Usage: python -m evaluation.full_run_extended {{{'|'.join(GROUPS)}}} "
              f"{{{'|'.join(SUPPORTED_CORRUPTIONS)}}}")
        sys.exit(1)
    group, corruption_type = sys.argv[1], sys.argv[2]
    datasets = GROUPS[group]

    results = []
    for name in datasets:
        print(f"Loading {name}...")
        df = load_dataset(name)
        for rate in CORRUPTION_RATES:
            for seed in SEEDS:
                r = run_one(name, df, seed, rate, corruption_type)
                results.append(r)
                print(
                    f"  {name:30s} {corruption_type} rate={rate:.2f} seed={seed} "
                    f"| auto n/p={r['automated']['n']}/{r['automated']['p']} "
                    f"sigma_cv={r['automated']['sigma_cv']:.4f} G={r['automated']['G']:+.4f} "
                    f"| manual G={r['manual']['G']:+.4f} "
                    f"| {r['elapsed_seconds']}s"
                )

    out_path = RESULTS_DIR / f"{group.replace('-', '_')}_{corruption_type}_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nWrote {len(results)} runs ({len(datasets)} datasets x {len(CORRUPTION_RATES)} rates x "
          f"{len(SEEDS)} seeds x 2 pipelines) to {out_path}")

    total_time = sum(r["elapsed_seconds"] for r in results)
    print(f"Total wall-clock time: {total_time:.1f}s across {len(results)} runs "
          f"({total_time/len(results):.3f}s/run average)")


if __name__ == "__main__":
    main()
