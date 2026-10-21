"""
Study 3 RQ9 transfer runner (docs/study3_protocol.md Section 4).

Runs the identical Study 2 grid on 8 binary PMLB datasets with 500 < n <= 1000,
none of them among the 44 raw PMLBmini candidates and none previously touched by
this project.

These datasets are EXPLICITLY OUTSIDE the project's n <= 500 small-data regime
and are not added to it. They exist to test whether thresholds fitted on the 25
small datasets transfer to a larger-n population -- a declared population
difference, reported separately and never pooled with the 25.

Several are synthetic boolean-function benchmarks of the same family as mux6,
corral and parity5, so Study 2 Section 5's forces_duplication stratification
applies and is recorded per run.
"""
import json
from pathlib import Path

from evaluation.full_run_study2 import CONDITIONS, SEEDS, load_dataset, run_one

RESULTS_DIR = Path(__file__).resolve().parent / "results"

TRANSFER_DATASETS = [
    "threeOf9", "monk3", "monk1", "monk2", "profb", "tic_tac_toe", "tokyo1", "xd6",
]


def main():
    results, skipped = [], []
    for name in TRANSFER_DATASETS:
        print(f"Loading {name}...")
        df = load_dataset(name)
        for corruption_type, rate in CONDITIONS:
            for seed in SEEDS:
                try:
                    r = run_one(name, df, seed, corruption_type, rate)
                except Exception as exc:  # noqa: BLE001 -- logged, never silent
                    skipped.append({"dataset": name, "seed": seed,
                                    "corruption_type": corruption_type or "clean",
                                    "rate": rate, "error": f"{type(exc).__name__}: {exc}"})
                    print(f"  SKIPPED {name} {corruption_type} {rate} seed={seed}: {exc}")
                    continue
                results.append(r)
        a = results[-1]["automated"]
        print(f"  {name:14s} done | n/p={a['n']}/{a['p']} epv={a['epv']:.2f} "
              f"forces_dup={results[-1]['forces_duplication']}")

    out = RESULTS_DIR / "study3_transfer_results.json"
    with open(out, "w") as f:
        json.dump({"population": "binary PMLB, 500 < n <= 1000, outside the n<=500 regime",
                   "runs": results, "skipped": skipped}, f, indent=2)
    print(f"\nWrote {len(results)} runs to {out} (skipped {len(skipped)})")


if __name__ == "__main__":
    main()
