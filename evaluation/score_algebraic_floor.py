"""POST-HOC re-analysis: the algebraic floor on within-dataset concordance, and the
CV-mean confound in the diagnostic's sub-chance reading.

THIS IS POST-HOC. It was not pre-registered. It re-measures the 525 runs already
stored in results/study4_estimators_results.json and adds no new runs. Label it
post-hoc wherever any figure from it is reported.

Why it exists
-------------
Two numbers were quoted in discussion without a script behind them. Both are now
computed here, so `grep -rln permut evaluation/` and the equivalent for the
residualised reading stop returning nothing.

1. THE ALGEBRAIC FLOOR. Within a dataset, the selected CV mean reaches a high
   concordance against the `poor_optimism` label, far above the diagnostic's. That
   looks like an unexploited per-run signal and it is not one: the outcome is

       G = s_cv_selected - s_test,   poor_optimism = (G > delta_G)

   so s_cv_selected and -s_test are ADDITIVE COMPONENTS of their own outcome. Any
   component of G scores well against a threshold on G by construction.

   The permutation null isolates that. Within each dataset, s_test values are
   re-paired at random against fixed s_cv_selected values, G and the label are
   rebuilt from the shuffled pair, and the concordance is recomputed. Shuffling
   destroys any genuine run-level association while preserving the algebra and
   each dataset's marginal distributions. Whatever concordance survives is the
   floor, not signal. A component whose observed value sits inside its own
   permutation interval carries no demonstrable per-run information.

   This is the correct reference point for reading the diagnostic's own
   within-dataset concordance. It is NOT evidence that the pipeline holds a
   better per-run signal than the warning it ships.

2. THE CV-MEAN CONFOUND. The diagnostic's within-dataset concordance reads below
   0.5 in places, which previously invited the reading that sigma "runs backwards"
   within a dataset. sigma and the CV mean are strongly negatively related within
   a dataset (a bounded metric near its ceiling cannot vary much), and the CV mean
   is the first term of G. So part of the sub-chance reading may be the confound
   rather than a reversal.

   Rank-residualising sigma on the CV mean within each dataset removes the
   component of sigma that the CV mean explains, and the concordance is recomputed
   on the residual. If the result returns to ~0.5, the apparent reversal was the
   confound and the honest statement is a null, not a direction.

Design notes
------------
- Reuses score_stratified's own `stratified_concordance` and `cluster_bootstrap`
  rather than reimplementing them, so pair formation, tie handling, exclusion of
  single-class strata and dataset-level resampling all match the published
  figures exactly.
- Fixed seeds throughout (PERMUTATION_SEED, BOOTSTRAP_SEED). Deterministic.
- Results written to results/algebraic_floor_scores.json.
- Reads only. No run record is modified and no model is refitted.

Run from the REPO ROOT:
    backend/venv/bin/python3 -m evaluation.score_algebraic_floor
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from evaluation.score_stratified import (
    BOOTSTRAP_SEED,
    DIAGNOSTICS,
    N_BOOTSTRAP,
    RESULTS_DIR,
    cluster_bootstrap,
    stratified_concordance,
)

SOURCE_FILE = "study4_estimators_results.json"
OUTPUT_FILE = "algebraic_floor_scores.json"

# delta_G is frozen at the Study 2 value and copied, never recomputed here.
DELTA_G = 0.05

PERMUTATION_SEED = 0
N_PERMUTATIONS = 400

# The diagnostic the paper is about, plus the two additive components of G.
SIGMA_FIELD = "sigma_R20"
COMPONENTS = {
    "cv_mean": lambda a: a["s_cv_selected"],
    "neg_s_test": lambda a: -a["s_test"],
    "sigma_R20": lambda a: a[SIGMA_FIELD],
}

WITHIN_DATASET = lambda row: row["dataset"]  # noqa: E731

# score_stratified.stratified_concordance reads the direction of "worse" from its
# own DIAGNOSTICS table, so the variables analysed here are registered into it at
# import time. All four point the same way: a larger value should mean a larger G,
# i.e. more over-optimism, which is what `True` (higher_is_worse) encodes.
#   cv_mean        larger CV estimate  -> larger G = s_cv - s_test
#   neg_s_test     larger -s_test      -> smaller s_test -> larger G
#   sigma_R20      the diagnostic under study, same direction as sigma_cv
#   sigma_residual sigma with the CV-mean component removed, direction preserved
# These registrations are additive and do not alter any existing entry, so the
# published figures from score_stratified are unaffected.
for _name in ("cv_mean", "neg_s_test", SIGMA_FIELD, "sigma_residual"):
    DIAGNOSTICS.setdefault(_name, True)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def load_rows():
    """One flat row per run, carrying the raw components so G can be rebuilt."""
    path = RESULTS_DIR / SOURCE_FILE
    if not path.exists():
        raise SystemExit(
            f"{path} not found. Run `python3 -m evaluation.full_run_study4` first."
        )
    with path.open() as fh:
        payload = json.load(fh)

    rows = []
    for record in payload["runs"]:
        a = record.get("automated")
        if not a:
            continue
        rows.append(
            {
                "dataset": record["dataset"],
                "family": record["corruption_type"],
                "rate": record["rate"],
                "s_cv": a["s_cv_selected"],
                "s_test": a["s_test"],
                "sigma": a[SIGMA_FIELD],
                "n_train": a["n"],
                # The published between-dataset figure is on sigma_cv (the R=1
                # estimator Study 2 used), not on the 20-repeat estimator, so it
                # is carried separately rather than reusing SIGMA_FIELD.
                "sigma_cv": a["sigma_cv"],
                # Frozen label, copied from the stored record rather than
                # recomputed, so the observed figures match the published ones.
                "poor": bool(a["labels"]["poor_optimism"]),
                "values": {name: fn(a) for name, fn in COMPONENTS.items()},
            }
        )
    return rows, payload.get("pre_registered_commit")


# ---------------------------------------------------------------------------
# 1. Permutation null on the algebraic floor
# ---------------------------------------------------------------------------
def _by_dataset(rows):
    groups = {}
    for row in rows:
        groups.setdefault(row["dataset"], []).append(row)
    return groups


def permuted_rows(rows, rng):
    """Re-pair s_test against s_cv WITHIN each dataset, then rebuild G and the label.

    Shuffling inside the dataset preserves each dataset's marginal distribution of
    both components and the algebraic identity G = s_cv - s_test, while destroying
    any run-level correspondence between them.
    """
    out = []
    for _dataset, group in _by_dataset(rows).items():
        shuffled = [row["s_test"] for row in group]
        rng.shuffle(shuffled)
        for row, s_test in zip(group, shuffled):
            g = row["s_cv"] - s_test
            out.append(
                {
                    "dataset": row["dataset"],
                    "family": row["family"],
                    "rate": row["rate"],
                    "poor": bool(g > DELTA_G),
                    "values": {
                        "cv_mean": row["s_cv"],
                        "neg_s_test": -s_test,
                        "sigma_R20": row["sigma"],
                    },
                }
            )
    return out


def permutation_null(rows, diagnostic, n=N_PERMUTATIONS, seed=PERMUTATION_SEED):
    rng = random.Random(seed)
    draws = []
    for _ in range(n):
        value = stratified_concordance(
            permuted_rows(rows, rng), diagnostic, WITHIN_DATASET
        )["concordance"]
        if value is not None:
            draws.append(value)
    if not draws:
        return {"mean": None, "lo": None, "hi": None, "n_draws": 0}
    draws.sort()
    mean = sum(draws) / len(draws)
    return {
        "mean": mean,
        "lo": draws[int(0.025 * len(draws))],
        "hi": draws[min(len(draws) - 1, int(0.975 * len(draws)))],
        "n_draws": len(draws),
        "dropped": n - len(draws),
    }


# ---------------------------------------------------------------------------
# 2. Rank-residualising sigma on the CV mean, within dataset
# ---------------------------------------------------------------------------
def _ranks(values):
    """Average ranks, ties shared, 1-based."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        shared = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            out[order[k]] = shared
        i = j + 1
    return out


def residualise_within_dataset(rows):
    """Replace sigma by its residual from an OLS fit on the CV mean, on ranks,
    fitted separately inside each dataset.

    Ranks rather than raw values because every concordance figure in this project
    is rank-based, so the residual stays on the scale the outcome is measured on.
    A dataset whose CV-mean ranks are constant has no slope to remove; its sigma
    is centred and otherwise left alone.
    """
    out = []
    for _dataset, group in _by_dataset(rows).items():
        x = _ranks([row["s_cv"] for row in group])
        y = _ranks([row["sigma"] for row in group])
        n = len(group)
        mx = sum(x) / n
        my = sum(y) / n
        sxx = sum((xi - mx) ** 2 for xi in x)
        sxy = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
        slope = (sxy / sxx) if sxx > 0 else 0.0
        for row, xi, yi in zip(group, x, y):
            residual = (yi - my) - slope * (xi - mx)
            out.append(
                {
                    "dataset": row["dataset"],
                    "family": row["family"],
                    "rate": row["rate"],
                    "poor": row["poor"],
                    "values": {"sigma_residual": residual},
                }
            )
    return out


# ---------------------------------------------------------------------------
# 3. Between-dataset ordering, and whether dataset size explains it
# ---------------------------------------------------------------------------
def _pearson(xs, ys):
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    den = (
        sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys)
    ) ** 0.5
    return num / den if den else None


def size_confound(rows):
    """Between-dataset Spearman rho(mean sigma_cv, poor rate), and the same
    correlation with training-set size partialled out.

    The obvious objection to a between-dataset association is that it is really
    a sample-size effect: small datasets are both noisier and more likely to
    fail. Training-set size does correlate strongly and negatively with the
    diagnostic, so the objection is live and has to be answered rather than
    asserted away. A first-order partial correlation on ranks answers it.
    """
    by_dataset = {}
    for row in rows:
        by_dataset.setdefault(row["dataset"], []).append(row)

    sigma, poor_rate, n_train = [], [], []
    for _dataset, group in sorted(by_dataset.items()):
        sigma.append(sum(r["sigma_cv"] for r in group) / len(group))
        poor_rate.append(sum(1 for r in group if r["poor"]) / len(group))
        n_train.append(sum(r["n_train"] for r in group) / len(group))

    rs, rp, rn = _ranks(sigma), _ranks(poor_rate), _ranks(n_train)
    r_sp = _pearson(rs, rp)
    r_sn = _pearson(rs, rn)
    r_pn = _pearson(rp, rn)
    partial = None
    if None not in (r_sp, r_sn, r_pn):
        denom = ((1 - r_sn ** 2) * (1 - r_pn ** 2)) ** 0.5
        partial = (r_sp - r_sn * r_pn) / denom if denom else None
    return {
        "n_datasets": len(sigma),
        "spearman_sigma_cv_vs_poor_rate": r_sp,
        "spearman_sigma_cv_vs_n_train": r_sn,
        "spearman_poor_rate_vs_n_train": r_pn,
        "partial_controlling_n_train": partial,
        "interpretation": (
            "dataset size does not explain the between-dataset association if the "
            "partial is close to the unadjusted correlation"
        ),
    }


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
def analyse():
    rows, source_commit = load_rows()
    datasets = sorted({row["dataset"] for row in rows})

    result = {
        "analysis": "algebraic floor on within-dataset concordance (POST-HOC)",
        "post_hoc": True,
        "pre_registered": False,
        "source_file": SOURCE_FILE,
        "source_pre_registered_commit": source_commit,
        "sigma_field": SIGMA_FIELD,
        "delta_g": DELTA_G,
        "label": "poor_optimism",
        "n_runs": len(rows),
        "n_datasets": len(datasets),
        "stratification": "within_dataset",
        "n_permutations": N_PERMUTATIONS,
        "permutation_seed": PERMUTATION_SEED,
        "n_bootstrap": N_BOOTSTRAP,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "observed": {},
        "permutation_null": {},
        "residualised": {},
        "between_dataset": {},
    }

    for name in COMPONENTS:
        observed = stratified_concordance(rows, name, WITHIN_DATASET)
        ci = cluster_bootstrap(
            rows,
            lambda sample, d=name: stratified_concordance(
                sample, d, WITHIN_DATASET
            )["concordance"],
        )
        null = permutation_null(rows, name)
        inside = (
            None
            if observed["concordance"] is None or null["lo"] is None
            else bool(null["lo"] <= observed["concordance"] <= null["hi"])
        )
        excess = (
            None
            if observed["concordance"] is None or null["mean"] is None
            else observed["concordance"] - null["mean"]
        )
        result["observed"][name] = {
            "concordance": observed["concordance"],
            "n_pairs": observed.get("n_pairs"),
            "n_strata_used": observed.get("n_strata_used"),
            "n_strata_excluded": observed.get("n_strata_excluded"),
            "ci_low": ci.get("ci_low"),
            "ci_high": ci.get("ci_high"),
        }
        result["permutation_null"][name] = dict(
            null,
            excess_over_null=excess,
            observed_inside_null_interval=inside,
        )

    result["between_dataset"] = size_confound(rows)

    # The primary comparison is about sigma_cv (R=1), the estimator the library
    # actually computes. SIGMA_FIELD is sigma_R20, so residualise BOTH and report
    # them separately rather than letting the R20 figure stand in for the shipped one.
    rows_r1 = [dict(r, sigma=r["sigma_cv"]) for r in rows]
    residual_r1 = stratified_concordance(
        residualise_within_dataset(rows_r1), "sigma_residual", WITHIN_DATASET)
    result["residualised"]["sigma_cv_on_cv_mean"] = {
        "concordance": residual_r1["concordance"],
        "n_pairs": residual_r1.get("n_pairs"),
        "n_strata_used": residual_r1.get("n_strata_used"),
        "estimator": "sigma_cv (R=1), as shipped",
    }

    residual_rows = residualise_within_dataset(rows)
    residual_observed = stratified_concordance(
        residual_rows, "sigma_residual", WITHIN_DATASET
    )
    residual_ci = cluster_bootstrap(
        residual_rows,
        lambda sample: stratified_concordance(
            sample, "sigma_residual", WITHIN_DATASET
        )["concordance"],
    )
    result["residualised"]["sigma_on_cv_mean"] = {
        "concordance": residual_observed["concordance"],
        "n_pairs": residual_observed.get("n_pairs"),
        "n_strata_used": residual_observed.get("n_strata_used"),
        "ci_low": residual_ci.get("ci_low"),
        "ci_high": residual_ci.get("ci_high"),
        "raw_sigma_concordance": result["observed"][SIGMA_FIELD]["concordance"],
    }
    return result


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def fmt(value, width=6):
    return "   n/a" if value is None else f"{value:{width}.4f}"


def report(result):
    print()
    print("POST-HOC: algebraic floor on within-dataset concordance")
    print(f"  source      {result['source_file']}")
    print(f"  runs        {result['n_runs']} over {result['n_datasets']} datasets")
    print(f"  label       {result['label']} at delta_G={result['delta_g']}")
    print(
        f"  null        {result['n_permutations']} permutations, "
        f"seed {result['permutation_seed']}"
    )
    print()
    print(
        f"  {'variable':<12} {'observed':>9} {'clustered CI':>18} "
        f"{'null mean':>10} {'null 95%':>18} {'excess':>8}  inside?"
    )
    for name in COMPONENTS:
        obs = result["observed"][name]
        null = result["permutation_null"][name]
        ci = f"[{fmt(obs['ci_low'],5)},{fmt(obs['ci_high'],5)}]"
        ni = f"[{fmt(null['lo'],5)},{fmt(null['hi'],5)}]"
        inside = {True: "YES", False: "no", None: "n/a"}[
            null["observed_inside_null_interval"]
        ]
        print(
            f"  {name:<12} {fmt(obs['concordance'],9)} {ci:>18} "
            f"{fmt(null['mean'],10)} {ni:>18} "
            f"{fmt(null['excess_over_null'],8)}  {inside}"
        )
    print()
    print("  A variable whose observed value lies INSIDE its own permutation")
    print("  interval carries no demonstrable within-dataset information: the")
    print("  concordance is a consequence of G = s_cv - s_test, not of signal.")
    print()
    res = result["residualised"]["sigma_on_cv_mean"]
    r1 = result["residualised"]["sigma_cv_on_cv_mean"]
    print("  sigma_cv (R=1, as shipped) residualised on the CV mean  %s" % fmt(r1["concordance"]))
    print("  sigma rank-residualised on the CV mean, within dataset:")
    print(f"    raw        {fmt(res['raw_sigma_concordance'])}")
    print(
        f"    residual   {fmt(res['concordance'])}   "
        f"CI [{fmt(res['ci_low'],5)},{fmt(res['ci_high'],5)}]   "
        f"({res['n_pairs']} pairs, {res['n_strata_used']} strata)"
    )
    print()
    bd = result["between_dataset"]
    print("  between-dataset ordering (%d datasets):" % bd["n_datasets"])
    print("    rho(sigma_cv, poor rate)     %s" % fmt(bd["spearman_sigma_cv_vs_poor_rate"]))
    print("    rho(sigma_cv, n_train)       %s" % fmt(bd["spearman_sigma_cv_vs_n_train"]))
    print("    partial, n_train controlled  %s" % fmt(bd["partial_controlling_n_train"]))
    print()
    print("  If the residual returns to ~0.5, the sub-chance raw reading is the")
    print("  CV-mean confound and the honest report is a null, not a direction.")
    print()


def main():
    result = analyse()
    report(result)
    out = Path(RESULTS_DIR) / OUTPUT_FILE
    with out.open("w") as fh:
        json.dump(result, fh, indent=2)
    print(f"Written: {out}")


if __name__ == "__main__":
    main()
