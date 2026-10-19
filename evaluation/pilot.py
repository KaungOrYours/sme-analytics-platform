"""
Required pilot study (approved PDM plan, Objective 2): before freezing the
protocol, confirm n/p and sigma_CV can actually be extracted from 2-3
development datasets, and measure the actual rate of poor outcomes (G >
some trial delta_G) and pipeline runtime. Results here inform the frozen
numeric choices (delta_G, corruption level, wall-clock budget B) written
into docs/evaluation_protocol.md -- NOT the other way around.

This script is exploratory by design: it intentionally tries a couple of
missing-value rates and reports raw G values rather than assuming a
delta_G, since delta_G must be frozen independently of what's observed
here per the approved plan's own anti-optimistic-bias requirement.

Usage: python -m evaluation.pilot
"""
import json
import time
from pathlib import Path

from pmlb import fetch_data

from evaluation.diagnostics import run_automated, run_manual_baseline, split_outer
from evaluation.injectors import inject_missing_values

RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

PILOT_DATASETS = ["molecular_biology_promoters", "appendicitis", "biomed"]
BIOMED_DROP_COLUMNS = [
    "Observation_number", "Hospital_identification_number_for_blood_sample", "Date_that_blood_sample_was_taken"
]
SEEDS = [1, 2, 3]
TRIAL_MISSING_RATES = [0.0, 0.15, 0.35]  # 0.0 = clean condition


def load_pilot_dataset(name):
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
    results = []
    for name in PILOT_DATASETS:
        print(f"Loading {name}...")
        df = load_pilot_dataset(name)
        for missing_rate in TRIAL_MISSING_RATES:
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

    out_path = RESULTS_DIR / "pilot_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nWrote {len(results)} pilot runs to {out_path}")

    g_values = [r["automated"]["G"] for r in results]
    print(f"\nG (automated) range: [{min(g_values):+.4f}, {max(g_values):+.4f}], "
          f"mean={sum(g_values)/len(g_values):+.4f}")
    total_time = sum(r["elapsed_seconds"] for r in results)
    print(f"Total pilot wall-clock time: {total_time:.1f}s across {len(results)} runs "
          f"({total_time/len(results):.2f}s/run average)")


if __name__ == "__main__":
    main()
