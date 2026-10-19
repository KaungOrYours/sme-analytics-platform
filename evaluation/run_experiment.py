"""
End-to-end smoke test for the evaluation harness, NOT the full protocol run.

docs/evaluation_protocol.md Section 3 describes the full grid: ~10-14
datasets x 4 error types x {5,10,20}% rates x multiple seeds, for the 3-4
deep-dive datasets, plus a lighter single pass on the rest. That full run
needs docs/datasets.md's shortlist locked first.

This script instead runs every piece of the harness (injectors,
cleaning_eval, comparison_runner, warnings_eval) against the one verified
placeholder dataset (Wholesale customers), at a small grid, so the harness
itself is proven correct before spending real compute on the full run.

Usage: python -m evaluation.run_experiment
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from evaluation.cleaning_eval import run_cleaning_evaluation
from evaluation.comparison_runner import run_comparison
from evaluation.datasets import load_wholesale_customers
from evaluation.warnings_eval import is_poor_performance

RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# Smoke-test grid - deliberately small. The locked protocol's full grid is
# {5,10,20}% x all 4 error types x many more seeds, on the real shortlist.
ERROR_TYPES = ["missing_values", "duplicates", "outliers"]
RATES = [0.05, 0.10, 0.20]
SEEDS = [1, 2, 3]


def run_cleaning_smoke_test(df):
    results = []
    for error_type in ERROR_TYPES:
        for rate in RATES:
            for seed in SEEDS:
                results.append(run_cleaning_evaluation(df, error_type, rate, seed))
    return results


def run_comparison_and_warnings_smoke_test(df, meta):
    comparisons = []
    run_records = []

    for seed in SEEDS:
        comparison = run_comparison(df, meta["problem_type"], meta["target_col"], seed=seed)
        comparisons.append(comparison)

        comp = comparison["comparison"]
        if comp["automated_cv_score"] is None or comp["automated_test_score"] is None:
            continue

        poor, detail = is_poor_performance(
            meta["problem_type"],
            cv_score=comp["automated_cv_score"],
            test_score=comp["automated_test_score"],
            majority_baseline=comp["majority_baseline"],
        )
        run_records.append({
            "seed": seed,
            "reliability_warnings": comparison["automated"]["reliability_warnings"],
            "poor": poor,
            "poor_detail": detail,
        })

    return comparisons, run_records


def main():
    df, meta = load_wholesale_customers()
    print(f"Loaded {meta['name']}: {df.shape}")

    if not meta["has_categorical_column"]:
        print(
            "NOTE: this dataset has no categorical column, so "
            "'inconsistent_categories' is skipped here. The locked dataset "
            "shortlist (docs/datasets.md) needs at least one dataset with "
            "categorical features to exercise that error type at all."
        )

    cleaning_results = run_cleaning_smoke_test(df)
    print(
        f"Ran {len(cleaning_results)} cleaning-evaluation cycles "
        f"({len(ERROR_TYPES)} error types x {len(RATES)} rates x {len(SEEDS)} seeds)"
    )

    comparisons, run_records = run_comparison_and_warnings_smoke_test(df, meta)
    print(f"Ran {len(comparisons)} automated-vs-manual comparison runs")
    print(f"Labelled {sum(r['poor'] for r in run_records)}/{len(run_records)} runs as 'poor' "
          f"under the locked definition (only {len(SEEDS)} seeds here - too few to score "
          f"warning precision/recall meaningfully; see run_records in the output file)")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = RESULTS_DIR / f"smoke_test_{timestamp}.json"
    with open(out_path, "w") as f:
        json.dump({
            "dataset": meta,
            "cleaning_results": cleaning_results,
            "comparisons": comparisons,
            "run_records": run_records,
        }, f, indent=2, default=str)
    print(f"Wrote results to {out_path}")


if __name__ == "__main__":
    main()
