"""
Study 4 runner (docs/study4_protocol.md, PRE-REGISTERED and committed 2026-10-23
in `7cab9db`, before this file existed).

Recomputes the cross-validation-variance diagnostic for every Study 2 run under
estimators of increasing precision, holding EVERYTHING ELSE FROZEN at Study 2's
values:

    outcome label      Study 2's poor_optimism at delta_G = 0.05, copied verbatim
    splits/corruption  reproduced from the same (dataset, seed, type, rate)
    model selection    the model Study 2 selected, re-fitted, never re-selected
    build_preprocessor untouched

Estimators (protocol Section 4), all for the SELECTED model only:

    sigma_R1        one 5-fold split, std(ddof=1) of 5 scores   -- as shipped
    sigma_R10       mean of per-repeat stds over repeats 0..9
    sigma_R20       mean of per-repeat stds over repeats 0..19
    sigma_pooled20  std(ddof=1) over all 100 fold scores        -- different estimand

Plus the RQ11 decoupling probe (protocol Section 5):

    sigma_even      mean per-repeat std over the 10 even-indexed repeats
    G_decoupled     mean fold score over the 10 ODD-indexed repeats, minus s_test

The 20 repeats are computed once and every other quantity is derived from them,
so the cost is 5 + 100 = 105 fits of the selected model per run rather than one
pass per estimator.

VALIDATION GATE (protocol Section 4): sigma_R1 must reproduce Study 2's stored
sigma_cv exactly for every run. The script reports the gate and refuses to write
results if it fails, because no comparison is meaningful if the reproduction is
wrong.

    python -m evaluation.full_run_study4            # all three groups
    python -m evaluation.full_run_study4 --groups A # a subset, for smoke tests
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np

from evaluation import backend_path  # noqa: F401
from evaluation.diagnostics import (
    AUTOMATED_CANDIDATES,
    cv_scores_for_model,
    split_outer,
)
from evaluation.full_run_study2 import (
    RESULTS_DIR,
    corrupt_training_partition,
    load_dataset,
)
from services.automl import build_preprocessor
from sklearn.pipeline import Pipeline

N_REPEATS = 20
REPEAT_SEED_BASE = 1000
GROUPS = ("A", "B", "C")
OUT_PATH = Path(RESULTS_DIR) / "study4_estimators_results.json"


def repeat_fold_scores(model_name, X_train, y_train, n_repeats=N_REPEATS):
    """Fold-score vector for each of n_repeats independent 5-fold splits of the
    SAME training partition. Repeat r uses random_state REPEAT_SEED_BASE + r,
    which is disjoint from the run seeds (1, 2, 3) by construction."""
    make_model = AUTOMATED_CANDIDATES[model_name]
    per_repeat = []
    for r in range(n_repeats):
        seed_r = REPEAT_SEED_BASE + r
        pipeline = Pipeline(
            [("preprocess", build_preprocessor(X_train)),
             ("model", make_model(seed_r))]
        )
        per_repeat.append(cv_scores_for_model(pipeline, X_train, y_train, seed_r))
    return per_repeat


def std_or_none(scores):
    arr = np.asarray(scores, dtype=float)
    return float(arr.std(ddof=1)) if arr.size >= 2 else None


def mean_of_repeat_stds(per_repeat, idx):
    """Mean over selected repeats of each repeat's own 5-fold std. This
    estimates the SAME quantity the shipped rule estimates, with len(idx) times
    the data -- not a pooled std, which would absorb between-repeat variation."""
    stds = [std_or_none(per_repeat[i]) for i in idx]
    stds = [s for s in stds if s is not None]
    return float(np.mean(stds)) if stds else None


def estimators_for_run(record, X_train, y_train, run_seed):
    """All Study 4 estimators for one run's automated-pipeline record."""
    model_name = record["model_name"]

    # sigma_R1: the shipped estimator, recomputed for the selected model with
    # the run's own seed. This is the validation gate.
    pipeline = Pipeline(
        [("preprocess", build_preprocessor(X_train)),
         ("model", AUTOMATED_CANDIDATES[model_name](run_seed))]
    )
    r1_scores = cv_scores_for_model(pipeline, X_train, y_train, run_seed)

    per_repeat = repeat_fold_scores(model_name, X_train, y_train)
    all_scores = np.concatenate(per_repeat)

    evens = [i for i in range(N_REPEATS) if i % 2 == 0]
    odds = [i for i in range(N_REPEATS) if i % 2 == 1]
    odd_mean = float(np.mean(np.concatenate([per_repeat[i] for i in odds])))

    return {
        "sigma_R1": std_or_none(r1_scores),
        "sigma_R10": mean_of_repeat_stds(per_repeat, range(10)),
        "sigma_R20": mean_of_repeat_stds(per_repeat, range(N_REPEATS)),
        "sigma_pooled20": std_or_none(all_scores),
        "sigma_even": mean_of_repeat_stds(per_repeat, evens),
        "G_decoupled": odd_mean - record["s_test"],
        "_r1_scores": [float(v) for v in r1_scores],
        "_n_fits": int(len(r1_scores) + all_scores.size),
    }


def main():
    ap = argparse.ArgumentParser(description="Study 4: estimator-precision comparison.")
    ap.add_argument("--groups", nargs="+", default=list(GROUPS), choices=list(GROUPS))
    args = ap.parse_args()

    out_runs, gate_failures, skipped = [], [], []
    started = time.time()

    for group in args.groups:
        src = Path(RESULTS_DIR) / f"study2_group_{group}_results.json"
        if not src.exists():
            raise SystemExit(f"{src} not found -- Study 4 reuses Study 2's grid.")
        with open(src) as f:
            study2_runs = json.load(f)["runs"]

        print(f"\n=== group {group}: {len(study2_runs)} runs ===", flush=True)
        cache = {}
        for i, r in enumerate(study2_runs, 1):
            name = r["dataset"]
            if name not in cache:
                cache[name] = load_dataset(name)
            df = cache[name]
            seed = r["seed"]

            X_train, X_test, y_train, y_test = split_outer(df, "target", seed)
            # Study 2 stores the clean condition as the string "clean"
            # (full_run_study2.py:140, `corruption_type or "clean"`); the
            # injector dispatch expects None. Invert that mapping here so the
            # reproduced partition is byte-identical to Study 2's.
            ctype = None if r["corruption_type"] == "clean" else r["corruption_type"]
            X_train, y_train = corrupt_training_partition(
                X_train, y_train, ctype, r["rate"], seed
            )

            a = r["automated"]
            try:
                est = estimators_for_run(a, X_train, y_train, seed)
            except ValueError as exc:
                skipped.append({"dataset": name, "seed": seed,
                                "corruption_type": r["corruption_type"],
                                "rate": r["rate"], "reason": str(exc)})
                print(f"  SKIPPED {name} {r['corruption_type']} seed={seed}: {exc}")
                continue

            # Validation gate: shipped estimator must reproduce exactly.
            stored = a.get("sigma_cv")
            got = est["sigma_R1"]
            if stored is None or got is None:
                match = stored is None and got is None
            else:
                match = abs(stored - got) < 1e-12
            if not match:
                gate_failures.append({"dataset": name, "seed": seed,
                                      "corruption_type": r["corruption_type"],
                                      "rate": r["rate"],
                                      "stored_sigma_cv": stored, "recomputed_sigma_R1": got})

            automated = {
                "model_name": a["model_name"],
                "s_cv_selected": a["s_cv_selected"],
                "s_test": a["s_test"],
                "G": a["G"],
                "n": a["n"],
                "p": a["p"],
                "sigma_cv": a["sigma_cv"],          # Study 2's value, carried through
                "labels": a["labels"],              # FROZEN outcome, not recomputed
                **{k: v for k, v in est.items() if not k.startswith("_")},
            }
            out_runs.append({
                "dataset": name,
                "group": group,
                "seed": seed,
                "corruption_type": r["corruption_type"],
                "rate": r["rate"],
                "automated": automated,
            })
            if i % 10 == 0 or i == len(study2_runs):
                print(f"  {i}/{len(study2_runs)} ({time.time()-started:.0f}s elapsed)", flush=True)

    elapsed = time.time() - started
    print(f"\n{len(out_runs)} runs, {len(skipped)} skipped, {elapsed:.0f}s")
    print(f"VALIDATION GATE: {len(gate_failures)} mismatches out of {len(out_runs)}")

    if gate_failures:
        print("\nGATE FAILED -- results NOT written. First 5 mismatches:")
        for g in gate_failures[:5]:
            print(f"  {g}")
        raise SystemExit(1)

    payload = {
        "protocol": "docs/study4_protocol.md",
        "pre_registered_commit": "7cab9db",
        "groups": args.groups,
        "n_repeats": N_REPEATS,
        "repeat_seed_base": REPEAT_SEED_BASE,
        "outcome": "Study 2 poor_optimism at delta_G=0.05, frozen and copied, not recomputed",
        "validation_gate": {"checked": len(out_runs), "mismatches": 0},
        "elapsed_seconds": round(elapsed, 1),
        "skipped": skipped,
        "runs": out_runs,
    }
    with open(OUT_PATH, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
