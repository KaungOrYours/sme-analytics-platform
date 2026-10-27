"""
Post-hoc delta_G sensitivity re-analysis (written 2026-10-27), closing open
item 1 of `docs/review_response_2026-10-22.md`.

**THIS IS NOT PRE-REGISTERED AND IS SENSITIVITY-ONLY** (the reviewer's own
qualifier, row 10 of the disposition table). `delta_G = 0.05` is a round
number fixed before the full-protocol results existed, informed only by the
pilot's ~11% poor-rate at that cutoff (`evaluation_protocol.md` Section 4).
It is a convenience threshold, not a validated boundary between "poor" and
"not poor" -- this script asks whether the project's headline conclusions
move if that single convenience number is varied, nothing more. It produces
NO new pipeline runs: every number here recomputes the "poor_optimism" label
from each run's already-collected raw G, at five round-number deltas that
bracket the frozen anchor by roughly half, 1.5x, 2x and 3x, and rescales two
already-published analyses against the five labels: Study 2's own fixed-
threshold confusion-matrix scoring (`score_study2.py`) and the post-hoc
stratified concordance (`score_stratified.py`). If the qualitative pattern
(within-dataset concordance at/near chance; pooled/between-dataset ordering
strong; no diagnostic's fixed-threshold MCC changes sign) holds across the
whole grid, delta_G's exact value is not what is carrying the finding. If it
does not hold, that is reported as a real limitation, not smoothed over.

Scope, matching the headline claims this is testing: Study 2 groups B and C
and the Study 3 transfer sample -- the three sources behind the project's
current Contribution 1/2 figures in `docs/findings.md`. Group A (Study 1's
original 7 spent datasets) is excluded for the same reason `score_stratified.py
all` excludes it: it is not part of the confirmatory evidence being defended
here. Re-running the sensitivity grid over Study 1/3/4's own result files
would be a further, separate piece of work and is not claimed to be done by
this script.

Usage:
    python -m evaluation.score_delta_sensitivity
"""
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from evaluation.diagnostics2 import DIAGNOSTIC_NAMES
from evaluation.score_rq2 import bootstrap_aggregate_metrics, confusion, mcc, precision_recall_far
from evaluation.score_stratified import (
    DIAGNOSTICS,
    STRATIFICATIONS,
    cluster_bootstrap,
    diagnostic_value,
    load_runs,
    stratified_concordance,
)

RESULTS_DIR = Path(__file__).resolve().parent / "results"

# Anchor (0.05) plus four round-number alternatives bracketing it by roughly
# half, 1.5x, 2x and 3x -- chosen before looking at any result in this script,
# for the same reason the anchor itself was a round number: a grid picked
# after seeing which values flatter the headline would defeat the point of a
# sensitivity check.
DELTA_GRID = [0.025, 0.05, 0.075, 0.10, 0.15]
ANCHOR = 0.05

SOURCES = ["study2_B", "study2_C", "study3_transfer"]
SOURCE_FILES = {
    "study2_B": "study2_group_B_results.json",
    "study2_C": "study2_group_C_results.json",
    "study3_transfer": "study3_transfer_results.json",
}

TRIGGERED_KEY_FOR_DIAGNOSTIC = {
    "sigma_cv": "sigma_cv_gt_0.10",
    "evalml_cov": "evalml_cov_gt_0.2",
    "evalml_range": "evalml_range_ge_0.5",
    "fold_contamination": "fold_contamination_gt_0.10",
    "epv": "epv_lt_10",
    "n_over_p": "np_lt_10",
}
assert set(TRIGGERED_KEY_FOR_DIAGNOSTIC.values()) == set(DIAGNOSTIC_NAMES)


def load(source):
    path = RESULTS_DIR / SOURCE_FILES[source]
    with open(path) as f:
        return json.load(f)["runs"]


def rows_at_delta(runs, delta):
    """Same flat row shape as score_stratified.extract(), but "poor" is
    recomputed from the raw G at the given delta rather than read from the
    precomputed (delta=0.05) labels dict."""
    rows = []
    for r in runs:
        a = r["automated"]
        rows.append(
            {
                "dataset": r["dataset"],
                "family": r["corruption_type"],
                "rate": r["rate"],
                "values": {d: diagnostic_value(a, d) for d in DIAGNOSTICS},
                "triggered": a["triggered"],
                "poor": bool(a["G"] > delta),
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Fixed-threshold confusion-matrix scoring, rescaled across the delta grid
# ---------------------------------------------------------------------------
def score_fixed_thresholds(rows, diagnostic, seed=0):
    key = TRIGGERED_KEY_FOR_DIAGNOSTIC[diagnostic]
    trig, poor = [], []
    for r in rows:
        t = r["triggered"][key]
        if t is None:
            continue
        trig.append(bool(t))
        poor.append(r["poor"])
    if not trig:
        return None
    tp, fp, fn, tn = confusion(trig, poor)
    m = mcc(tp, fp, fn, tn)
    ci = bootstrap_aggregate_metrics(trig, poor, seed=seed)
    return {
        "n_poor": sum(poor),
        "n_runs": len(poor),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "mcc": m,
        "mcc_ci": ci["mcc"],
    }


# ---------------------------------------------------------------------------
# Threshold-free concordance, rescaled across the delta grid
# ---------------------------------------------------------------------------
def score_concordance(rows, diagnostic):
    out = {}
    for sname in ("pooled", "within_dataset"):
        keyfn = STRATIFICATIONS[sname]
        point = stratified_concordance(rows, diagnostic, keyfn)
        ci = cluster_bootstrap(
            rows, lambda rs, d=diagnostic, k=keyfn: stratified_concordance(rs, d, k)["concordance"]
        )
        out[sname] = {**point, **ci}
    return out


def analyse_source(source):
    runs = load(source)
    by_delta = {}
    for delta in DELTA_GRID:
        rows = rows_at_delta(runs, delta)
        n_poor = sum(1 for r in rows if r["poor"])
        diags = {}
        for diag in DIAGNOSTICS:
            diags[diag] = {
                "fixed_threshold": score_fixed_thresholds(rows, diag),
                "concordance": score_concordance(rows, diag),
            }
        by_delta[delta] = {"n_poor": n_poor, "n_runs": len(rows), "diagnostics": diags}
    return {"source": source, "n_datasets": len({r["dataset"] for r in runs}), "by_delta": by_delta}


def fmt_mcc(entry):
    if entry is None:
        return "   undef"
    ci = entry["mcc_ci"]
    if ci is None:
        return f"{entry['mcc']:7.3f}  [undef]"
    return f"{entry['mcc']:7.3f}  [{ci['ci_lower']:5.2f},{ci['ci_upper']:5.2f}]"


def fmt_conc(entry):
    c = entry["concordance"]
    if c is None:
        return "    NA"
    lo, hi = entry["ci_low"], entry["ci_high"]
    if lo is None:
        return f"{c:.3f} [NA]"
    return f"{c:.3f} [{lo:.2f},{hi:.2f}]"


def report(result):
    src = result["source"]
    print(f"\n{'=' * 90}")
    print(f"DELTA_G SENSITIVITY (not pre-registered, sensitivity-only) -- {src}")
    print(f"{'=' * 90}")
    print(f"{result['n_datasets']} source datasets. Grid: {DELTA_GRID} (anchor = {ANCHOR}).")
    print("\npoor_optimism rate by delta_G:")
    for delta in DELTA_GRID:
        d = result["by_delta"][delta]
        tag = " <- anchor" if delta == ANCHOR else ""
        print(f"  delta_G={delta:.3f}: {d['n_poor']:3d}/{d['n_runs']} poor "
              f"({100*d['n_poor']/d['n_runs']:.1f}%){tag}")

    for diag in DIAGNOSTICS:
        print(f"\n-- {diag} --")
        print(f"  {'delta_G':>8}{'fixed-thresh MCC [CI]':>28}{'pooled concordance':>28}{'within-ds concordance':>28}")
        for delta in DELTA_GRID:
            d = result["by_delta"][delta]["diagnostics"][diag]
            tag = "*" if delta == ANCHOR else " "
            print(
                f" {tag}{delta:7.3f}"
                f"{fmt_mcc(d['fixed_threshold']):>28}"
                f"{fmt_conc(d['concordance']['pooled']):>28}"
                f"{fmt_conc(d['concordance']['within_dataset']):>28}"
            )


def main():
    results = {src: analyse_source(src) for src in SOURCES}
    for src in SOURCES:
        report(results[src])
    out = RESULTS_DIR / "delta_g_sensitivity_scores.json"
    with open(out, "w") as f:
        json.dump(
            {
                "pre_registered": False,
                "label": "sensitivity-only, per review_response_2026-10-22.md open item 1",
                "delta_grid": DELTA_GRID,
                "anchor": ANCHOR,
                "sources": results,
            },
            f,
            indent=2,
        )
    print(f"\nWritten: {out}")


if __name__ == "__main__":
    main()
