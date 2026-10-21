"""
Study 2 grid runner (docs/study2_protocol.md, PRE-REGISTERED 2026-10-21).

Runs the Section 7 analysis plan's grid for one dataset group:

    {clean, missing_values 15/35%, duplicates 15/35%, outliers 15/35%}
    x {seed 1, 2, 3} x {automated, manual baseline}

= 7 conditions x 3 seeds = 21 runs per dataset, each producing both pipelines.

Study 1's runners (`full_run.py`, `full_run_extended.py`,
`full_run_sample_size.py`) are left untouched -- Study 1's frozen results stay
reproducible from the code that produced them. This script exists because Study
2 needs all three corruption families plus clean in ONE results file per group,
with the four new diagnostics attached, which none of the Study 1 runners emit.

ORDER MATTERS AND IS PRE-REGISTERED. Run groups A and B first, score them, and
only then run group C once:

    python -m evaluation.full_run_study2 A
    python -m evaluation.full_run_study2 B
    python -m evaluation.full_run_study2 C     # NOT before B has been scored

Group C is the confirmation holdout. Running it early does not technically break
anything in code, but it destroys the one thing that makes Study 2's claims
credible. The script prints a warning and requires --confirm for group C so that
it cannot happen by reflex or by shell history.

`inconsistent_categories` is not offered: all 25 TabMini-eligible datasets are
100% numerically encoded (verified 2026-10-21 across the full set, not just
Study 1's 7), so that injector is a guaranteed no-op here.
"""
import argparse
import json
import time
from pathlib import Path

from pmlb import fetch_data

from evaluation.diagnostics import run_automated, run_manual_baseline, split_outer
from evaluation.diagnostics2 import (
    forces_duplication,
    measure_all,
    outcome_labels,
    triggered_flags,
)
from evaluation.injectors import INJECTORS

RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)
SPLIT_FILE = Path(__file__).resolve().parent / "study2_dataset_split.json"
CACHE_DIR = Path(__file__).resolve().parent / "data" / "pmlb_cache"

SEEDS = [1, 2, 3]

# (corruption_type, rate). None = the clean condition.
CONDITIONS = [
    (None, 0.0),
    ("missing_values", 0.15),
    ("missing_values", 0.35),
    ("duplicates", 0.15),
    ("duplicates", 0.35),
    ("outliers", 0.15),
    ("outliers", 0.35),
]

BIOMED_DROP_COLUMNS = [
    "Observation_number",
    "Hospital_identification_number_for_blood_sample",
    "Date_that_blood_sample_was_taken",
]


def load_groups():
    with open(SPLIT_FILE) as f:
        split = json.load(f)
    return {
        "A": split["group_A_exploratory_burned"],
        "B": split["group_B_development_extension"],
        "C": split["group_C_confirmation"],
    }


def load_dataset(name):
    df = fetch_data(name, local_cache_dir=str(CACHE_DIR))
    if name == "biomed":
        # Study 1's frozen column-drop rule, carried forward unchanged.
        df = df.drop(columns=[c for c in BIOMED_DROP_COLUMNS if c in df.columns])
    return df


def corrupt_training_partition(X_train, y_train, corruption_type, rate, seed):
    """Apply one injector to the training partition only. The test partition is
    never passed to this function, which is how Study 1 enforces that it stays
    clean -- the same ordering is preserved here deliberately."""
    if corruption_type is None:
        return X_train, y_train

    train_df = X_train.copy()
    train_df["target"] = y_train
    feature_cols = list(X_train.columns)
    injector = INJECTORS[corruption_type]

    if corruption_type == "duplicates":
        # Duplicates whole rows, target included -- correct, since a duplicated
        # row's label must travel with its features.
        corrupted, _ = injector(train_df, rate, seed)
    else:
        # missing_values and outliers default to every matching-dtype column,
        # which would include the numeric "target" if not scoped out.
        corrupted, _ = injector(train_df, rate, seed, columns=feature_cols)

    return corrupted.drop(columns=["target"]), corrupted["target"]


def run_one(name, df, seed, corruption_type, rate):
    start = time.time()
    X_train, X_test, y_train, y_test = split_outer(df, "target", seed)
    X_train, y_train = corrupt_training_partition(
        X_train, y_train, corruption_type, rate, seed
    )

    automated = run_automated(X_train, y_train, X_test, y_test, seed)
    manual = run_manual_baseline(X_train, y_train, X_test, y_test, seed)

    # p is a property of the preprocessor fitted on X_train, so it is identical
    # for both pipelines; run_manual_baseline does not return it, so the
    # automated run's value is reused rather than recomputed.
    p = automated["p"]
    manual["p"] = p

    for record in (automated, manual):
        record.update(measure_all(X_train, y_train, p, record["cv_scores"], seed))
        record["triggered"] = triggered_flags(record)
        record["labels"] = outcome_labels(record["G"])

    return {
        "dataset": name,
        "seed": seed,
        "corruption_type": corruption_type or "clean",
        "rate": rate,
        "forces_duplication": bool(forces_duplication(X_train)),
        "elapsed_seconds": round(time.time() - start, 2),
        "automated": automated,
        "manual": manual,
    }


def main():
    groups = load_groups()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("group", choices=sorted(groups))
    ap.add_argument(
        "--confirm",
        action="store_true",
        help="required for group C, the pre-registered confirmation holdout",
    )
    args = ap.parse_args()

    if args.group == "C" and not args.confirm:
        print(
            "Group C is the PRE-REGISTERED CONFIRMATION HOLDOUT "
            "(docs/study2_protocol.md Section 3).\n"
            "It must be run once, after groups A and B have been scored, with "
            "every threshold exactly as frozen.\n"
            "Re-run with --confirm if that is genuinely where you are."
        )
        raise SystemExit(2)

    datasets = groups[args.group]
    results, skipped = [], []

    for name in datasets:
        print(f"Loading {name}...")
        df = load_dataset(name)
        for corruption_type, rate in CONDITIONS:
            for seed in SEEDS:
                try:
                    r = run_one(name, df, seed, corruption_type, rate)
                except Exception as exc:  # noqa: BLE001 -- logged, never silent
                    skipped.append(
                        {
                            "dataset": name,
                            "seed": seed,
                            "corruption_type": corruption_type or "clean",
                            "rate": rate,
                            "error": f"{type(exc).__name__}: {exc}",
                        }
                    )
                    print(f"  SKIPPED {name} {corruption_type} {rate} seed={seed}: {exc}")
                    continue
                results.append(r)
                a = r["automated"]
                print(
                    f"  {name:28s} {r['corruption_type']:15s} rate={rate:.2f} seed={seed} "
                    f"| n/p={a['n']}/{a['p']} epv={a['epv']:.2f} "
                    f"contam={a['fold_contamination']:.3f} "
                    f"G={a['G']:+.4f} | {r['elapsed_seconds']}s"
                )

    out_path = RESULTS_DIR / f"study2_group_{args.group}_results.json"
    with open(out_path, "w") as f:
        json.dump({"group": args.group, "runs": results, "skipped": skipped}, f, indent=2)

    total = sum(r["elapsed_seconds"] for r in results)
    print(
        f"\nWrote {len(results)} runs ({len(datasets)} datasets x {len(CONDITIONS)} "
        f"conditions x {len(SEEDS)} seeds) to {out_path}"
    )
    print(f"Skipped: {len(skipped)}")
    if results:
        print(f"Total wall-clock: {total:.1f}s ({total/len(results):.3f}s/run)")


if __name__ == "__main__":
    main()
