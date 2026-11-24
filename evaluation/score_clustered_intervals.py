"""POST-HOC re-analysis: every headline interval re-derived at the correct unit of
analysis, and the recalibration gains given a paired interval for the first time.

THIS IS POST-HOC. It was not pre-registered. It re-measures runs already stored and
adds none. Label it post-hoc wherever any figure from it is reported.

Why it exists
-------------
Runs are nested in datasets. One dataset contributes 21 runs through 7 conditions x
3 seeds, and those 21 runs share a dataset, a target definition, a class balance and
an n/p ratio. They are not exchangeable.

score_rq2.bootstrap_aggregate_metrics resamples the RUN, which treats them as
exchangeable and therefore understates uncertainty. Its own docstring defends the
choice on the grounds that a dataset-level cluster bootstrap "would be far noisier,
not more rigorous". That reasoning is wrong and this module supersedes it:

  - Width is not validity. A clustered interval is wider because the run-level one
    has the wrong coverage, so "noisier" describes the correct answer rather than an
    argument against it.
  - score_stratified.cluster_bootstrap, in this same package, states the opposite
    ("produces anti-conservative intervals") and is the convention the later studies
    adopted. Two modules cannot justify opposite choices for the same problem.
  - Where a cluster count is genuinely too small, the right output is "not estimable
    at this cluster count", which is the standard applied everywhere else here.

Two things are computed.

PART A -- binary discrimination per diagnostic, per group, with the run-level
interval and the dataset-clustered interval side by side, and an explicit flag for
every figure whose exclusion of the null does not survive clustering.

PART B -- the leave-one-dataset-out recalibration gain, with a PAIRED
dataset-clustered interval. recalibrate_study3 pools the 25 disjoint out-of-sample
confusion matrices before bootstrapping and stores no per-dataset matrix, so no
clustered interval was computable from its output; the gains were reported as bare
point estimates. Here the per-dataset matrices are retained, and the anchor and the
recalibrated arm are scored on the SAME bootstrap resample so the shared sampling
noise cancels and the interval is on the difference rather than on two separate
quantities.

Validation gate
---------------
Before any new figure is produced, the published run-level MCCs are recomputed from
the stored records and compared against recalibrate_study3's own frozen output. If
any disagrees, the module aborts rather than reporting. This is the same gate Study 4
used, for the same reason: a re-analysis is only meaningful if it first reproduces
what it is re-analysing.

Nothing is refitted and no model is trained. No existing results file is modified;
output goes to results/clustered_intervals_scores.json.

Run from the REPO ROOT:
    backend/venv/bin/python3 -m evaluation.score_clustered_intervals
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from evaluation.recalibrate_study3 import (
    DIAGNOSTIC_SPECS,
    LABEL,
    fit_threshold,
    load_runs,
)
from evaluation.recalibrate_study3 import triggered_at as _triggered_at_strict

# Diagnostics whose PRE-REGISTERED anchor rule is non-strict (">=", not ">").
# evalml_range is the only one: the frozen Study 2 rule and EvalML's own source
# both use ">= 0.5", and evaluation/diagnostics2.py implements it that way.
# recalibrate_study3.triggered_at applies a generic strict ">", which on this
# benchmark silently drops the 14 of 525 runs sitting at exactly 0.5 -- 28
# firings instead of 42, and an anchor MCC of 0.1036 instead of the
# pre-registered 0.0891. That is an undeclared deviation from a frozen rule.
#
# This module does NOT edit recalibrate_study3 (its output is published and must
# stay reproducible as published). It applies the pre-registered comparator here
# and records the divergence in its own output so the two can be reconciled.
NON_STRICT_AT_ANCHOR = {"evalml_range"}

for _n, _spec in DIAGNOSTIC_SPECS.items():
    _spec.setdefault("_name", _n)


def triggered_at(value, threshold, direction, name=None, anchor=None):
    """As recalibrate_study3.triggered_at, except that a diagnostic whose frozen
    rule is non-strict is evaluated non-strictly AT ITS ANCHOR.

    Only at the anchor: a refitted threshold is a continuous grid point, where
    strict and non-strict agree except on measure-zero ties, and the LODO fit in
    recalibrate_study3 used the strict form.
    """
    if value is None:
        return None
    if (
        direction > 0
        and name in NON_STRICT_AT_ANCHOR
        and anchor is not None
        and threshold == anchor
    ):
        return bool(value >= threshold)
    return _triggered_at_strict(value, threshold, direction)
from evaluation.score_rq2 import confusion, mcc

RESULTS_DIR = Path(__file__).resolve().parent / "results"
OUTPUT_FILE = "clustered_intervals_scores.json"

N_BOOTSTRAP = 2000
BOOTSTRAP_SEED = 0

# Minimum independent clusters before an interval is reported at all. Below this a
# percentile interval is not meaningfully estimable and the module says so instead
# of printing a narrower number from the wrong unit.
MIN_CLUSTERS = 3

GROUPS = {"A": ("A",), "B": ("B",), "C": ("C",), "all25": ("A", "B", "C")}


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------
def score_at(runs, spec, threshold):
    """(mcc, n_scored, degenerate) for one diagnostic at one threshold.

    Undefined diagnostic values are dropped and counted, never coerced to False.
    Returns mcc=None when the scored subset has a single outcome class, which is a
    genuinely undefined MCC rather than a zero.
    """
    trig, poor = [], []
    for r in runs:
        t = triggered_at(
            r[spec["key"]], threshold, spec["direction"],
            name=spec.get("_name"), anchor=spec["anchor"],
        )
        if t is None:
            continue
        trig.append(t)
        poor.append(r["poor"])
    if not trig or len(set(poor)) < 2:
        return None, len(trig), True
    tp, fp, fn, tn = confusion(trig, poor)
    degenerate = (tp + fp) == 0 or (tp + fn) == 0 or (tn + fp) == 0 or (tn + fn) == 0
    return mcc(tp, fp, fn, tn), len(trig), degenerate


def percentile_ci(draws):
    if not draws:
        return None, None, 0
    ordered = sorted(draws)
    lo = ordered[int(0.025 * len(ordered))]
    hi = ordered[min(len(ordered) - 1, int(0.975 * len(ordered)))]
    return lo, hi, len(ordered)


def run_level_ci(runs, spec, threshold, seed=BOOTSTRAP_SEED, n=N_BOOTSTRAP):
    """The interval as previously published: resample runs, ignoring nesting.

    Reproduced here only so the two can be shown side by side. It is not the
    interval this module recommends.
    """
    rng = np.random.default_rng(seed)
    idx_pool = list(range(len(runs)))
    draws = []
    for _ in range(n):
        idx = rng.integers(0, len(idx_pool), size=len(idx_pool))
        value, _, _ = score_at([runs[i] for i in idx], spec, threshold)
        if value is not None:
            draws.append(value)
    lo, hi, kept = percentile_ci(draws)
    return {"ci_low": lo, "ci_high": hi, "n_draws": kept, "unit": "run"}


def cluster_ci(runs, spec, threshold, seed=BOOTSTRAP_SEED, n=N_BOOTSTRAP):
    """Resample whole DATASETS with replacement. All of a dataset's runs travel
    together, so the interval reflects the number of independent datasets.

    A dataset drawn twice contributes its runs twice, which is the correct
    behaviour for a cluster bootstrap on a pooled statistic.
    """
    by_dataset = {}
    for r in runs:
        by_dataset.setdefault(r["dataset"], []).append(r)
    datasets = sorted(by_dataset)
    if len(datasets) < MIN_CLUSTERS:
        return {
            "ci_low": None,
            "ci_high": None,
            "n_draws": 0,
            "unit": "dataset",
            "not_estimable": True,
            "reason": f"{len(datasets)} clusters, minimum {MIN_CLUSTERS}",
        }
    rng = np.random.default_rng(seed)
    draws, dropped, degenerate = [], 0, 0
    for _ in range(n):
        picks = rng.integers(0, len(datasets), size=len(datasets))
        sample = []
        for p in picks:
            sample.extend(by_dataset[datasets[p]])
        value, _, is_degenerate = score_at(sample, spec, threshold)
        if value is None:
            dropped += 1
            continue
        # A resample in which the diagnostic never fires (or always fires) has a
        # zero marginal, and the frozen MCC convention returns exactly 0.0 for it.
        # Those draws are RETAINED, because dropping them would condition the
        # interval on the diagnostic having fired. But they are an imputation of
        # the null inside the bootstrap, so at small cluster counts they can set
        # the percentile bound by themselves -- which is visible as a lower bound
        # of exactly 0.000. Counted here so the interval can be read correctly.
        if is_degenerate:
            degenerate += 1
        draws.append(value)
    lo, hi, kept = percentile_ci(draws)
    return {
        "ci_low": lo,
        "ci_high": hi,
        "n_draws": kept,
        "n_dropped": dropped,
        "n_degenerate_resamples": degenerate,
        "share_degenerate": (degenerate / kept) if kept else None,
        "bound_set_by_degenerate": bool(lo is not None and lo == 0.0 and degenerate > 0),
        "n_clusters": len(datasets),
        "unit": "dataset",
    }


def excludes_zero(ci):
    if ci.get("ci_low") is None:
        return None
    return bool(ci["ci_low"] > 0 or ci["ci_high"] < 0)


# ---------------------------------------------------------------------------
# Validation gate
# ---------------------------------------------------------------------------
def validation_gate(runs):
    """Reproduce recalibrate_study3's frozen anchor MCCs before reporting anything new."""
    frozen_path = RESULTS_DIR / "study3_recalibration_scores.json"
    if not frozen_path.exists():
        return {"ran": False, "reason": f"{frozen_path.name} absent; gate skipped"}
    with frozen_path.open() as fh:
        frozen = json.load(fh)

    block = frozen.get("rq8") or frozen
    checks, mismatches = [], 0
    for name, spec in DIAGNOSTIC_SPECS.items():
        entry = block.get(name) or {}
        anchor = entry.get("anchor") or {}
        published = anchor.get("mcc")
        recomputed, _, _ = score_at(runs, spec, spec["anchor"])
        agree = (
            published is not None
            and recomputed is not None
            and abs(published - recomputed) < 1e-9
        )
        # One divergence is expected and declared: recalibrate_study3 scores
        # evalml_range with a strict ">" where the pre-registered rule is ">=".
        # This module uses the pre-registered comparator, so its anchor figure
        # for that diagnostic is deliberately NOT the published one. Recorded as
        # a declared deviation, not counted as a gate failure, and reported in
        # full so the two numbers can be reconciled rather than silently differ.
        declared = (not agree) and name in NON_STRICT_AT_ANCHOR
        if not agree and not declared:
            mismatches += 1
        checks.append(
            {
                "diagnostic": name,
                "published_anchor_mcc": published,
                "recomputed": recomputed,
                "agrees": agree,
                "declared_deviation": declared,
                "deviation_reason": (
                    "published figure uses a strict '>' comparator; the "
                    "pre-registered rule is '>=' and is used here. 14 of 525 "
                    "runs sit at exactly the anchor."
                    if declared
                    else None
                ),
            }
        )
    return {
        "ran": True,
        "checks": checks,
        "mismatches": mismatches,
        "declared_deviations": sum(1 for c in checks if c["declared_deviation"]),
    }


# ---------------------------------------------------------------------------
# PART A
# ---------------------------------------------------------------------------
def part_a(all_runs):
    out = {}
    for group_name, keys in GROUPS.items():
        runs = [r for r in all_runs if r["group"] in keys]
        if not runs:
            continue
        datasets = sorted({r["dataset"] for r in runs})
        block = {
            "n_runs": len(runs),
            "n_datasets": len(datasets),
            "n_poor": sum(1 for r in runs if r["poor"]),
            "diagnostics": {},
        }
        for name, spec in DIAGNOSTIC_SPECS.items():
            value, n_scored, degenerate = score_at(runs, spec, spec["anchor"])
            rl = run_level_ci(runs, spec, spec["anchor"])
            cl = cluster_ci(runs, spec, spec["anchor"])
            block["diagnostics"][name] = {
                "label": spec["label"],
                "anchor": spec["anchor"],
                "mcc": value,
                "n_scored": n_scored,
                "degenerate": degenerate,
                "run_level_ci": rl,
                "clustered_ci": cl,
                "run_level_excludes_zero": excludes_zero(rl),
                "clustered_excludes_zero": excludes_zero(cl),
                "significance_lost_under_clustering": bool(
                    excludes_zero(rl) and excludes_zero(cl) is False
                ),
            }
        out[group_name] = block
    return out


# ---------------------------------------------------------------------------
# PART B
# ---------------------------------------------------------------------------
def lodo_per_dataset(runs, spec):
    """Leave-one-dataset-out refit, retaining each held-out dataset's own confusion
    matrix for both the recalibrated threshold and the frozen anchor.

    This is what recalibrate_study3 discards: it pools the 25 matrices before
    bootstrapping, which makes a clustered interval impossible from its output.
    """
    datasets = sorted({r["dataset"] for r in runs})
    per_dataset = []
    for d in datasets:
        fit_runs = [r for r in runs if r["dataset"] != d]
        test_runs = [r for r in runs if r["dataset"] == d]
        t_star, fit_mcc = fit_threshold(fit_runs, spec)

        def matrix(threshold):
            trig, poor = [], []
            for r in test_runs:
                t = triggered_at(
                    r[spec["key"]], threshold, spec["direction"],
                    name=spec.get("_name"), anchor=spec["anchor"],
                )
                if t is None:
                    continue
                trig.append(t)
                poor.append(r["poor"])
            return confusion(trig, poor) if trig else (0, 0, 0, 0)

        per_dataset.append(
            {
                "held_out": d,
                "fitted_threshold": t_star,
                "fit_mcc_on_rest": fit_mcc,
                "recal": dict(zip(("tp", "fp", "fn", "tn"), matrix(t_star))),
                "anchor": dict(zip(("tp", "fp", "fn", "tn"), matrix(spec["anchor"]))),
            }
        )
    return per_dataset


def _pooled_mcc(cells):
    tp = sum(c["tp"] for c in cells)
    fp = sum(c["fp"] for c in cells)
    fn = sum(c["fn"] for c in cells)
    tn = sum(c["tn"] for c in cells)
    if (tp + fn) == 0 or (fp + tn) == 0:
        return None
    return mcc(tp, fp, fn, tn)


def paired_gain_ci(per_dataset, seed=BOOTSTRAP_SEED, n=N_BOOTSTRAP):
    """Dataset-clustered bootstrap on the DIFFERENCE recalibrated - anchor.

    The same resample scores both arms, so sampling noise common to them cancels
    and the interval is on the gain itself rather than being inferred from two
    separate intervals.
    """
    rng = np.random.default_rng(seed)
    k = len(per_dataset)
    if k < MIN_CLUSTERS:
        return {"ci_low": None, "ci_high": None, "not_estimable": True, "n_clusters": k}
    draws, dropped = [], 0
    for _ in range(n):
        picks = rng.integers(0, k, size=k)
        recal = _pooled_mcc([per_dataset[p]["recal"] for p in picks])
        anchor = _pooled_mcc([per_dataset[p]["anchor"] for p in picks])
        if recal is None or anchor is None:
            dropped += 1
        else:
            draws.append(recal - anchor)
    lo, hi, kept = percentile_ci(draws)
    return {
        "ci_low": lo,
        "ci_high": hi,
        "n_draws": kept,
        "n_dropped": dropped,
        "n_clusters": k,
        "unit": "dataset (paired)",
    }


def part_b(all_runs):
    out = {}
    for name, spec in DIAGNOSTIC_SPECS.items():
        per_dataset = lodo_per_dataset(all_runs, spec)
        recal = _pooled_mcc([p["recal"] for p in per_dataset])
        anchor = _pooled_mcc([p["anchor"] for p in per_dataset])
        gain = None if (recal is None or anchor is None) else recal - anchor
        ci = paired_gain_ci(per_dataset)
        thresholds = [p["fitted_threshold"] for p in per_dataset]
        out[name] = {
            "label": spec["label"],
            "anchor_threshold": spec["anchor"],
            "anchor_mcc": anchor,
            "recalibrated_oos_mcc": recal,
            "mcc_gain": gain,
            "paired_clustered_ci": ci,
            "gain_excludes_zero": excludes_zero(ci),
            "fitted_threshold_spread": {
                "min": min(thresholds),
                "max": max(thresholds),
                "median": float(np.median(thresholds)),
                "fold_range": (
                    None
                    if min(thresholds) == 0
                    else max(thresholds) / min(thresholds)
                ),
            },
            "per_dataset": per_dataset,
        }
    return out


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def fmt(v, w=7):
    return "    n/a" if v is None else f"{v:{w}.3f}"


def ci_str(ci):
    if ci.get("ci_low") is None:
        return "   not estimable"
    return f"[{ci['ci_low']:+.3f},{ci['ci_high']:+.3f}]"


def report(result):
    gate = result["validation_gate"]
    print()
    if gate.get("ran"):
        exact = sum(1 for c in gate["checks"] if c["agrees"])
        print(
            f"VALIDATION GATE: {exact}/{len(gate['checks'])} published anchor MCCs "
            f"reproduced exactly, {gate.get('declared_deviations', 0)} declared "
            f"deviation(s), {gate['mismatches']} unexplained"
        )
        for c in gate["checks"]:
            if c["agrees"]:
                continue
            kind = "DECLARED DEVIATION" if c["declared_deviation"] else "MISMATCH"
            print(
                f"  {kind} {c['diagnostic']}: published "
                f"{c['published_anchor_mcc']:.4f} vs pre-registered rule "
                f"{c['recomputed']:.4f}"
            )
            if c["deviation_reason"]:
                print(f"    {c['deviation_reason']}")
    else:
        print(f"VALIDATION GATE: skipped -- {gate.get('reason')}")

    print()
    print("PART A -- binary discrimination at the frozen anchor (POST-HOC)")
    for group_name, block in result["part_a"].items():
        print(
            f"\n  {group_name}: {block['n_runs']} runs, {block['n_datasets']} datasets, "
            f"{block['n_poor']} poor"
        )
        print(
            f"    {'diagnostic':<20} {'MCC':>7}  {'run-level CI':>16}  "
            f"{'clustered CI':>16}  verdict"
        )
        for name, d in block["diagnostics"].items():
            if d["significance_lost_under_clustering"]:
                verdict = "LOSES significance"
            elif d["clustered_excludes_zero"]:
                verdict = "survives"
            elif d["clustered_excludes_zero"] is None:
                verdict = "not estimable"
            else:
                verdict = "null either way"
            print(
                f"    {name:<20} {fmt(d['mcc'])}  {ci_str(d['run_level_ci']):>16}  "
                f"{ci_str(d['clustered_ci']):>16}  {verdict}"
            )

    print()
    print("PART B -- recalibration gain with a PAIRED clustered interval (POST-HOC)")
    print(
        f"    {'diagnostic':<20} {'anchor':>7} {'recal':>7} {'gain':>7}  "
        f"{'paired clustered CI':>19}  {'fitted t* range':>22}"
    )
    for name, d in result["part_b"].items():
        spread = d["fitted_threshold_spread"]
        rng_s = f"[{spread['min']:.4f}, {spread['max']:.4f}]"
        flag = "" if not d["gain_excludes_zero"] else "  <- excludes 0"
        print(
            f"    {name:<20} {fmt(d['anchor_mcc'])} {fmt(d['recalibrated_oos_mcc'])} "
            f"{fmt(d['mcc_gain'])}  {ci_str(d['paired_clustered_ci']):>19}  "
            f"{rng_s:>22}{flag}"
        )
    print()
    print("    A gain whose paired interval contains zero is not evidence that")
    print("    recalibration helps or hurts. Report the point estimate as such.")
    print()


def _plain(obj):
    """numpy scalars -> Python scalars, so json.dump cannot emit NaN/np.bool_.

    mcc() and the bootstrap return numpy types; json serialises np.bool_ not at
    all and np.float64 NaN as a bare `NaN`, which is invalid JSON. Non-finite
    values become null, which is what "undefined" should look like on disk.
    """
    import math

    if isinstance(obj, dict):
        return {k: _plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_plain(v) for v in obj]
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        value = float(obj)
        return value if math.isfinite(value) else None
    return obj


def main():
    runs = load_runs()
    gate = validation_gate(runs)
    if gate.get("ran") and gate["mismatches"]:
        report({"validation_gate": gate, "part_a": {}, "part_b": {}})
        raise SystemExit(
            "Validation gate failed: the stored records no longer reproduce the "
            "published anchor MCCs. Resolve that before trusting any figure here."
        )

    result = {
        "analysis": "headline intervals at the correct unit of analysis (POST-HOC)",
        "post_hoc": True,
        "pre_registered": False,
        "label": LABEL,
        "n_bootstrap": N_BOOTSTRAP,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "min_clusters_for_interval": MIN_CLUSTERS,
        "supersedes": (
            "score_rq2.bootstrap_aggregate_metrics for every reported interval, and "
            "recalibrate_study3's bare mcc_gain point estimates"
        ),
        "validation_gate": gate,
        "part_a": part_a(runs),
        "part_b": part_b(runs),
    }
    report(result)
    out = RESULTS_DIR / OUTPUT_FILE
    with out.open("w") as fh:
        json.dump(_plain(result), fh, indent=2, allow_nan=False)
    print(f"Written: {out}")


if __name__ == "__main__":
    main()
