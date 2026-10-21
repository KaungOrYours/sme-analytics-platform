"""
Study 3: leave-one-dataset-out threshold recalibration
(docs/study3_protocol.md, PRE-REGISTERED 2026-10-21 before any threshold was fitted).

Answers RQ8: can the diagnostics' thresholds be recalibrated so their binary
decisions recover the discrimination their continuous scores demonstrably carry,
and does a recalibrated threshold generalise to datasets not used to fit it?

Method, exactly as pre-registered:
  - resampling unit is the DATASET, not the run (runs within a dataset are
    correlated, so a threshold fitted on some of a dataset's runs would be
    evaluated on near-replicates of its own fitting data)
  - for each of the 25 datasets d: fit t* on the other 24 datasets' runs only,
    apply t* to d's runs, record that confusion matrix
  - aggregate the 25 disjoint out-of-sample matrices into one
  - fitting criterion: maximise MCC on the 24 fitting datasets' pooled runs,
    ties broken toward the published/frozen anchor value
  - grid: 200 equally-spaced candidates across the fitting runs' observed range
  - thresholds fitted POOLED across corruption families, because a deployed
    diagnostic does not know which corruption is present

Every number this script reports is out-of-sample. No dataset contributes to the
fit of the threshold it is evaluated under.

Usage:
    python -m evaluation.recalibrate_study3                  # RQ8 on the 25
    python -m evaluation.recalibrate_study3 --transfer       # + RQ9 on the 8
"""
import argparse
import json
from pathlib import Path

import numpy as np

from evaluation.score_rq2 import bootstrap_aggregate_metrics, confusion, mcc, precision_recall_far

RESULTS_DIR = Path(__file__).resolve().parent / "results"
N_GRID = 200  # pre-registered

# Each diagnostic as a continuous score plus the direction that means "risk",
# and the published/frozen anchor threshold it is being compared against.
# direction = +1 means "triggered when value > t"; -1 means "triggered when value < t".
DIAGNOSTIC_SPECS = {
    "np": {"key": "n_over_p", "direction": -1, "anchor": 10.0, "label": "n/p < t"},
    "epv": {"key": "epv", "direction": -1, "anchor": 10.0, "label": "EPV < t"},
    "sigma_cv": {"key": "sigma_cv", "direction": +1, "anchor": 0.10, "label": "sigma_cv > t"},
    "fold_contamination": {
        "key": "fold_contamination", "direction": +1, "anchor": 0.10,
        "label": "fold_contamination > t",
    },
    "evalml_cov": {"key": "evalml_cov", "direction": +1, "anchor": 0.2, "label": "evalml_cov > t"},
    "evalml_range": {
        "key": "evalml_range", "direction": +1, "anchor": 0.5, "label": "evalml_range > t",
    },
}
LABEL = "poor_optimism"  # pre-registered; no threshold is fitted against the others


def load_runs(groups=("A", "B", "C")):
    """All Study 2 runs across the 25 datasets, flattened to (dataset, scores, label)."""
    out = []
    for g in groups:
        path = RESULTS_DIR / f"study2_group_{g}_results.json"
        with open(path) as f:
            for r in json.load(f)["runs"]:
                a = r["automated"]
                out.append(
                    {
                        "dataset": r["dataset"],
                        "group": g,
                        "corruption_type": r["corruption_type"],
                        "forces_duplication": r["forces_duplication"],
                        "poor": bool(a["labels"][LABEL]),
                        "n_over_p": a["n"] / a["p"],
                        "epv": a["epv"],
                        "sigma_cv": a["sigma_cv"],
                        "fold_contamination": a["fold_contamination"],
                        "evalml_cov": a["evalml_cov"],
                        "evalml_range": a["evalml_range"],
                    }
                )
    return out


def triggered_at(value, threshold, direction):
    if value is None:
        return None
    return bool(value > threshold) if direction > 0 else bool(value < threshold)


def fit_threshold(runs, spec):
    """Maximise MCC over the pre-registered grid. Ties break toward the anchor.

    Returns (best_threshold, best_mcc_on_fitting_runs). Runs with an undefined
    diagnostic value are dropped from the fit, never coerced.
    """
    vals = [r[spec["key"]] for r in runs if r[spec["key"]] is not None]
    poor = [r["poor"] for r in runs if r[spec["key"]] is not None]
    if not vals or len(set(poor)) < 2:
        return spec["anchor"], None

    lo, hi = min(vals), max(vals)
    if lo == hi:
        return spec["anchor"], None
    grid = np.linspace(lo, hi, N_GRID)

    best_t, best_m = None, -np.inf
    for t in grid:
        trig = [triggered_at(v, t, spec["direction"]) for v in vals]
        m = mcc(*confusion(trig, poor))
        # Strict > keeps the first (lowest) maximiser; the anchor tie-break below
        # then pulls among equal-MCC candidates toward the published value.
        if m > best_m:
            best_t, best_m = float(t), m
    # Pre-registered tie-break: among thresholds achieving the best MCC, take the
    # one closest to the diagnostic's published/frozen anchor, so the procedure
    # cannot drift from the literature value without earning it.
    ties = []
    for t in grid:
        trig = [triggered_at(v, t, spec["direction"]) for v in vals]
        if mcc(*confusion(trig, poor)) == best_m:
            ties.append(float(t))
    if ties:
        best_t = min(ties, key=lambda t: abs(t - spec["anchor"]))
    return best_t, best_m


def evaluate(runs, spec, threshold):
    trig, poor = [], []
    for r in runs:
        t = triggered_at(r[spec["key"]], threshold, spec["direction"])
        if t is None:
            continue
        trig.append(t)
        poor.append(r["poor"])
    if not trig or len(set(poor)) < 2:
        return None, (trig, poor)
    tp, fp, fn, tn = confusion(trig, poor)
    precision, recall, far = precision_recall_far(tp, fp, fn, tn)
    return (
        {
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": precision, "recall": recall, "false_alarm_rate": far,
            "mcc": mcc(tp, fp, fn, tn),
            "degenerate": (tp + fp) == 0 or (tp + fn) == 0 or (tn + fp) == 0 or (tn + fn) == 0,
        },
        (trig, poor),
    )


def leave_one_dataset_out(runs):
    """RQ8. Returns per-diagnostic out-of-sample results plus the anchor baseline."""
    datasets = sorted({r["dataset"] for r in runs})
    results = {}

    for name, spec in DIAGNOSTIC_SPECS.items():
        oos_trig, oos_poor, per_dataset = [], [], []

        for d in datasets:
            fit_runs = [r for r in runs if r["dataset"] != d]
            test_runs = [r for r in runs if r["dataset"] == d]
            t_star, fit_mcc = fit_threshold(fit_runs, spec)
            _, (trig, poor) = evaluate(test_runs, spec, t_star)
            oos_trig.extend(trig)
            oos_poor.extend(poor)
            per_dataset.append(
                {
                    "held_out": d,
                    "fitted_threshold": t_star,
                    "fit_mcc_on_24": fit_mcc,
                    "n_test_runs": len(trig),
                    "n_test_poor": sum(poor),
                }
            )

        # Aggregate the 25 disjoint out-of-sample matrices.
        tp, fp, fn, tn = confusion(oos_trig, oos_poor)
        precision, recall, far = precision_recall_far(tp, fp, fn, tn)
        recal = {
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": precision, "recall": recall, "false_alarm_rate": far,
            "mcc": mcc(tp, fp, fn, tn),
            "n_runs": len(oos_trig), "n_poor": sum(oos_poor),
            "aggregate_bootstrap_ci": bootstrap_aggregate_metrics(oos_trig, oos_poor),
            "fitted_thresholds": {
                "min": min(p["fitted_threshold"] for p in per_dataset),
                "max": max(p["fitted_threshold"] for p in per_dataset),
                "median": float(np.median([p["fitted_threshold"] for p in per_dataset])),
            },
            "per_dataset": per_dataset,
        }

        # Baseline: the published/frozen anchor on the same runs.
        anchor_scores, (atrig, apoor) = evaluate(runs, spec, spec["anchor"])
        if anchor_scores is not None:
            anchor_scores["aggregate_bootstrap_ci"] = bootstrap_aggregate_metrics(atrig, apoor)
            anchor_scores["threshold"] = spec["anchor"]

        results[name] = {
            "label": spec["label"],
            "anchor": anchor_scores,
            "recalibrated_oos": recal,
            "mcc_gain": (
                None if anchor_scores is None
                else recal["mcc"] - anchor_scores["mcc"]
            ),
        }
    return results


def fit_on_all(runs):
    """Thresholds fitted on all 25 datasets -- used ONLY for the RQ9 transfer
    test, where the 8 larger datasets are the disjoint evaluation sample."""
    return {
        name: fit_threshold(runs, spec)[0] for name, spec in DIAGNOSTIC_SPECS.items()
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--transfer", action="store_true",
                    help="also score RQ9 on the 8 larger transfer datasets")
    args = ap.parse_args()

    runs = load_runs()
    print(f"Loaded {len(runs)} runs across {len({r['dataset'] for r in runs})} datasets "
          f"(label = {LABEL}, poor = {sum(r['poor'] for r in runs)})")

    results = leave_one_dataset_out(runs)

    print("\n=== RQ8: leave-one-dataset-out recalibration (all figures OUT-OF-SAMPLE) ===")
    print(f"{'diagnostic':20s} {'anchor t':>9s} {'anchor MCC':>11s} | "
          f"{'fitted t (median)':>18s} {'recal MCC':>10s} {'95% CI':>16s} {'gain':>8s}")
    for name, r in results.items():
        a, rc = r["anchor"], r["recalibrated_oos"]
        ci = rc["aggregate_bootstrap_ci"]["mcc"]
        am = f"{a['mcc']:11.3f}" if a else "          -"
        print(f"{name:20s} {DIAGNOSTIC_SPECS[name]['anchor']:9.3f} {am} | "
              f"{rc['fitted_thresholds']['median']:18.4f} {rc['mcc']:10.3f} "
              f"[{ci['ci_lower']:6.2f},{ci['ci_upper']:6.2f}] "
              f"{(r['mcc_gain'] if r['mcc_gain'] is not None else float('nan')):+8.3f}")
        tl = rc["fitted_thresholds"]
        print(f"{'':20s} fitted-threshold spread across the 25 folds: "
              f"[{tl['min']:.4f}, {tl['max']:.4f}]  "
              f"(prec {rc['precision'] if rc['precision'] is None else round(rc['precision'],3)}, "
              f"rec {rc['recall'] if rc['recall'] is None else round(rc['recall'],3)}, "
              f"FAR {rc['false_alarm_rate'] if rc['false_alarm_rate'] is None else round(rc['false_alarm_rate'],3)})")

    out = {
        "protocol": "docs/study3_protocol.md (pre-registered 2026-10-21)",
        "label": LABEL,
        "n_runs": len(runs),
        "n_datasets": len({r["dataset"] for r in runs}),
        "method": "leave-one-dataset-out; threshold fitted on 24, evaluated on the held-out 1",
        "rq8": results,
    }

    if args.transfer:
        tpath = RESULTS_DIR / "study3_transfer_results.json"
        if not tpath.exists():
            print(f"\n[RQ9 skipped] {tpath} not found -- run "
                  f"`python -m evaluation.full_run_study3_transfer` first.")
        else:
            with open(tpath) as f:
                traw = json.load(f)["runs"]
            trans = []
            for r in traw:
                a = r["automated"]
                trans.append({
                    "dataset": r["dataset"], "corruption_type": r["corruption_type"],
                    "forces_duplication": r["forces_duplication"],
                    "poor": bool(a["labels"][LABEL]),
                    "n_over_p": a["n"] / a["p"], "epv": a["epv"], "sigma_cv": a["sigma_cv"],
                    "fold_contamination": a["fold_contamination"],
                    "evalml_cov": a["evalml_cov"], "evalml_range": a["evalml_range"],
                })
            fitted = fit_on_all(runs)
            print(f"\n=== RQ9: transfer to {len({r['dataset'] for r in trans})} larger datasets "
                  f"({len(trans)} runs, poor = {sum(r['poor'] for r in trans)}) ===")
            print("Thresholds fitted on the 25 small datasets, applied unchanged. "
                  "Population differs (500 < n <= 1000) -- not pooled with RQ8.")
            print(f"{'diagnostic':20s} {'fitted t':>10s} {'MCC':>8s} {'95% CI':>16s} | "
                  f"{'anchor t':>9s} {'anchor MCC':>11s}")
            rq9 = {}
            for name, spec in DIAGNOSTIC_SPECS.items():
                s_fit, (ft, fp_) = evaluate(trans, spec, fitted[name])
                s_anc, (at, ap_) = evaluate(trans, spec, spec["anchor"])
                if s_fit:
                    s_fit["aggregate_bootstrap_ci"] = bootstrap_aggregate_metrics(ft, fp_)
                    ci = s_fit["aggregate_bootstrap_ci"]["mcc"]
                    ancm = f"{s_anc['mcc']:11.3f}" if s_anc else "          -"
                    print(f"{name:20s} {fitted[name]:10.4f} {s_fit['mcc']:8.3f} "
                          f"[{ci['ci_lower']:6.2f},{ci['ci_upper']:6.2f}] | "
                          f"{spec['anchor']:9.3f} {ancm}")
                rq9[name] = {"fitted_threshold": fitted[name],
                             "transfer_fitted": s_fit, "transfer_anchor": s_anc}
            out["rq9"] = {"fitted_on_25": fitted, "results": rq9,
                          "n_runs": len(trans),
                          "datasets": sorted({r["dataset"] for r in trans})}

    path = RESULTS_DIR / "study3_recalibration_scores.json"
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {path}")


if __name__ == "__main__":
    main()
