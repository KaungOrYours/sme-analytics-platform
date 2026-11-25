"""POST-HOC: the manuscript figures that previously had no producing module.

THIS IS POST-HOC. Not pre-registered. It re-measures stored runs and adds none.

Several figures reported in the write-up were computed inline and never emitted
by any module, so they could not be reproduced from the released artefact. That
is the exact gap that let an unpopulated `n_over_p` key reach an abstract once
already. This module closes it. Everything here reads stored run records only;
no pipeline run is re-executed and no frozen result is altered.

Emits, in order:

  1. between_dataset_rho    Spearman rho of mean sigma_CV against a dataset's
                            poor rate, over all 25 and over the subset where
                            the outcome is attainable, each with a
                            dataset-clustered interval.
  2. candidate_outcomes     The same rho against five candidate dataset-level
                            outcomes, which is what separates "orders by
                            instability" from "orders by optimism".
  3. selection_bias         Per-dataset mean G regressed on mean sigma_CV over
                            clean runs, the two control arms, and the
                            first-order selection prediction.
  4. exclusions             Leave-one-dataset-out jackknife on rho, and the
                            MLC++ Boolean exclusion.
  5. positives_concentration  Where the positive cases sit, and what rho does
                            when the largest contributors are removed.
  6. structural_screen      Features that partition the target exactly, WITH
                            the distinct-value share, so a feature that
                            partitions only because it is unique to each row is
                            separable from one that carries target information.

Reuses `score_stratified`'s frozen `cluster_bootstrap` and `spearman` and
`score_algebraic_floor`'s `load_rows` unchanged, so figures stay comparable
with the published ones.

Run from the REPO ROOT:
    backend/venv/bin/python3 -m evaluation.score_paper_figures
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

from evaluation.score_algebraic_floor import DELTA_G, RESULTS_DIR, load_rows
from evaluation.score_stratified import cluster_bootstrap, spearman

OUT_FILE = RESULTS_DIR / "paper_figures_scores.json"

# Three candidate classifiers, so the argmax is over three. Folds are treated as
# independent here, which they are not, so this is a LOWER bound on the
# predicted slope.
N_CANDIDATES = 3
N_FOLDS = 5
# E[max of 3 standard normals], by numerical integration rather than a quoted
# constant, so the figure is reproducible from this file alone.
def _expected_max_normal(m, n_grid=2_000_001, lo=-12.0, hi=12.0):
    z = np.linspace(lo, hi, n_grid)
    pdf = np.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)
    cdf = 0.5 * (1.0 + np.vectorize(math.erf)(z / math.sqrt(2.0)))
    return float(np.trapezoid(z * m * cdf ** (m - 1) * pdf, z))


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _g(row):
    return row["s_cv"] - row["s_test"]


def _by_dataset(rows):
    out = defaultdict(list)
    for row in rows:
        out[row["dataset"]].append(row)
    return out


def _rho_sigma_vs_poor(rows):
    """Spearman rho: dataset mean sigma_cv against dataset poor rate."""
    groups = _by_dataset(rows)
    means = [float(np.mean([r["sigma_cv"] for r in rs])) for rs in groups.values()]
    rates = [float(np.mean([1.0 if r["poor"] else 0.0 for r in rs])) for rs in groups.values()]
    return spearman(means, rates)


def _attainable(rows):
    """Datasets with at least one run above delta_G -- the outcome is reachable."""
    return {name for name, rs in _by_dataset(rows).items()
            if max(_g(r) for r in rs) > DELTA_G}


def _ols(xs, ys):
    if len(xs) < 2:
        return None, None
    x = np.asarray(xs, dtype=float)
    y = np.asarray(ys, dtype=float)
    vx = float(np.var(x))
    if vx == 0.0:
        return None, None
    slope = float(np.cov(x, y, bias=True)[0][1] / vx)
    return slope, float(np.mean(y) - slope * np.mean(x))


# ---------------------------------------------------------------------------
# 1. between-dataset rho, with its interval
# ---------------------------------------------------------------------------
def between_dataset_rho(rows):
    keep = _attainable(rows)
    estimable = [r for r in rows if r["dataset"] in keep]
    return {
        "all": {
            "rho": _rho_sigma_vs_poor(rows),
            "n_datasets": len(_by_dataset(rows)),
            **cluster_bootstrap(rows, _rho_sigma_vs_poor),
        },
        "estimable": {
            "rho": _rho_sigma_vs_poor(estimable),
            "n_datasets": len(keep),
            "definition": f"datasets with at least one run above delta_G = {DELTA_G}",
            **cluster_bootstrap(estimable, _rho_sigma_vs_poor),
        },
    }


# ---------------------------------------------------------------------------
# 2. what the diagnostic actually orders
# ---------------------------------------------------------------------------
OUTCOMES = {
    "sd_of_G": lambda rs: float(np.std([_g(r) for r in rs], ddof=1)) if len(rs) > 1 else None,
    "rate_abs_G_gt_delta": lambda rs: float(np.mean([abs(_g(r)) > DELTA_G for r in rs])),
    "rate_G_gt_delta_our_label": lambda rs: float(np.mean([1.0 if r["poor"] else 0.0 for r in rs])),
    "mean_G": lambda rs: float(np.mean([_g(r) for r in rs])),
    "rate_G_lt_minus_delta": lambda rs: float(np.mean([_g(r) < -DELTA_G for r in rs])),
}


def candidate_outcomes(rows):
    keep = _attainable(rows)
    out = {}
    for name, fn in OUTCOMES.items():
        def stat(rs, fn=fn):
            groups = _by_dataset(rs)
            xs, ys = [], []
            for g in groups.values():
                v = fn(g)
                if v is None:
                    continue
                xs.append(float(np.mean([r["sigma_cv"] for r in g])))
                ys.append(v)
            return spearman(xs, ys)
        est_rows = [r for r in rows if r["dataset"] in keep]
        out[name] = {
            "rho_all_25": stat(rows),
            "rho_estimable": stat(est_rows),
            "clustered_ci_all_25": cluster_bootstrap(rows, stat),
        }
    return out


# ---------------------------------------------------------------------------
# 3. selection bias
# ---------------------------------------------------------------------------
def selection_bias(rows):
    """Per-dataset mean G on mean sigma_CV, clean runs only.

    The control arm is the manual pipeline, which fits one prespecified model
    with no argmax. There are two defensible controls and they are NOT the same
    regression, so both are reported rather than one being passed off as "the"
    control: regressing the control's own G on the control's own sigma, and
    regressing the control's G on the automated arm's sigma.
    """
    # The control arm lives in the Study 2 group files; the Study 4 re-measurement
    # stores the automated arm only.
    clean = defaultdict(lambda: {"auto_s": [], "auto_g": [], "man_s": [], "man_g": []})
    for group in ("A", "B", "C"):
        with (RESULTS_DIR / f"study2_group_{group}_results.json").open() as fh:
            payload = json.load(fh)
        for record in payload["runs"]:
            if record["corruption_type"] != "clean":
                continue
            a, m = record.get("automated"), record.get("manual")
            if not a or not m:
                continue
            d = clean[record["dataset"]]
            d["auto_s"].append(a["sigma_cv"])
            d["auto_g"].append(a["s_cv_selected"] - a["s_test"])
            d["man_s"].append(m["sigma_cv"])
            d["man_g"].append(m["s_cv_selected"] - m["s_test"])

    names = sorted(clean)
    mean = lambda k: [float(np.mean(clean[n][k])) for n in names]
    slope, intercept = _ols(mean("auto_s"), mean("auto_g"))
    ctrl_own, _ = _ols(mean("man_s"), mean("man_g"))
    ctrl_cross, _ = _ols(mean("auto_s"), mean("man_g"))

    clean_rows = [r for r in rows if r["family"] == "clean"]

    def stat(rs):
        groups = _by_dataset(rs)
        xs = [float(np.mean([r["sigma_cv"] for r in g])) for g in groups.values()]
        ys = [float(np.mean([_g(r) for r in g])) for g in groups.values()]
        s, _i = _ols(xs, ys)
        return s

    e_max = _expected_max_normal(N_CANDIDATES)
    return {
        "n_datasets": len(names),
        "condition": "clean runs only",
        "automated_slope": slope,
        "automated_intercept": intercept,
        "control_own_sigma_slope": ctrl_own,
        "control_cross_sigma_slope": ctrl_cross,
        "control_note": (
            "control_own_sigma_slope regresses the control arm's G on the CONTROL's "
            "sigma; control_cross_sigma_slope regresses it on the AUTOMATED arm's "
            "sigma. They are different regressions and differ in sign."
        ),
        "expected_max_of_3_normals": e_max,
        "predicted_slope_coefficient": e_max / math.sqrt(N_FOLDS),
        "prediction_note": (
            "folds are treated as independent, which they are not, so this is a "
            "LOWER bound on the predicted slope"
        ),
        "clustered_ci": cluster_bootstrap(clean_rows, stat),
    }


# ---------------------------------------------------------------------------
# 4. exclusions and the jackknife
# ---------------------------------------------------------------------------
MLCPP_BOOLEAN = ["mux6", "parity5", "corral"]


def exclusions(rows):
    base_all = _rho_sigma_vs_poor(rows)
    keep = _attainable(rows)
    base_est = _rho_sigma_vs_poor([r for r in rows if r["dataset"] in keep])

    without_mlcpp = [r for r in rows if r["dataset"] not in MLCPP_BOOLEAN]
    est_wo = _attainable(without_mlcpp)

    jack = {}
    for name in sorted(_by_dataset(rows)):
        kept = [r for r in rows if r["dataset"] != name]
        jack[name] = _rho_sigma_vs_poor(kept) - base_all
    worst = max(jack.items(), key=lambda kv: abs(kv[1]))
    return {
        "rho_all_25": base_all,
        "rho_estimable": base_est,
        "mlcpp_boolean_excluded": {
            "datasets": MLCPP_BOOLEAN,
            "rho_remaining_22": _rho_sigma_vs_poor(without_mlcpp),
            "rho_remaining_estimable": _rho_sigma_vs_poor(
                [r for r in without_mlcpp if r["dataset"] in est_wo]),
            "n_estimable": len(est_wo),
        },
        "leave_one_dataset_out_delta": jack,
        "jackknife_range": [min(jack.values()), max(jack.values())],
        "most_influential": {"dataset": worst[0], "delta": worst[1]},
    }


# ---------------------------------------------------------------------------
# 5. where the positives are, and what happens without the biggest contributors
# ---------------------------------------------------------------------------
def positives_concentration(rows):
    counts = {name: sum(1 for r in rs if r["poor"]) for name, rs in _by_dataset(rows).items()}
    total = sum(counts.values())
    order = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    keep = _attainable(rows)

    def drop(names):
        sub = [r for r in rows if r["dataset"] not in names]
        sub_est = [r for r in sub if r["dataset"] in _attainable(sub)]
        return {
            "rho_all": _rho_sigma_vs_poor(sub),
            "n_all": len(_by_dataset(sub)),
            "rho_estimable": _rho_sigma_vs_poor(sub_est),
            "n_estimable": len(_by_dataset(sub_est)),
            "clustered_ci_estimable": cluster_bootstrap(sub_est, _rho_sigma_vs_poor),
        }

    top5 = [n for n, _ in order[:5]]
    cum, half_at = 0, None
    for i, (_n, c) in enumerate(order, start=1):
        cum += c
        if half_at is None and cum * 2 >= total:
            half_at = i
    return {
        "total_positives": total,
        "per_dataset": dict(order),
        "n_contributing": sum(1 for _n, c in order if c > 0),
        "n_zero": sum(1 for _n, c in order if c == 0),
        "n_datasets_supplying_half": half_at,
        "top5": top5,
        "top5_share": sum(counts[n] for n in top5) / total,
        "rho_without_top5": drop(set(top5)),
        "baseline": {
            "rho_all": _rho_sigma_vs_poor(rows),
            "rho_estimable": _rho_sigma_vs_poor([r for r in rows if r["dataset"] in keep]),
        },
    }


# ---------------------------------------------------------------------------
# 6. structural screen, WITH the uniqueness control
# ---------------------------------------------------------------------------
def structural_screen(dataset_names):
    """A feature partitions the target exactly if no value holds both classes.

    On small-n data that happens for free whenever a feature is near-unique per
    row: an all-distinct column partitions ANY target. Reporting the flag
    without distinct(f)/n therefore conflates leakage with uniqueness, so the
    share is reported for every flag and a flag at share 1.0 is marked trivial.
    """
    try:
        from pmlb import fetch_data
    except ImportError:
        return {"error": "pmlb not installed; screen not run"}

    out = {}
    for name in sorted(dataset_names):
        try:
            df = fetch_data(name)
        except Exception as exc:                     # noqa: BLE001 - reported, not hidden
            out[name] = {"error": str(exc)[:120]}
            continue
        n = len(df)
        flags = []
        for col in df.columns:
            if col == "target":
                continue
            groups = df.groupby(col)["target"].nunique()
            if (groups <= 1).all():
                share = float(df[col].nunique()) / n
                flags.append(
                    {"feature": col,
                     "distinct_share": share,
                     "trivial_all_distinct": share == 1.0}
                )
        dup = float(df.drop(columns=["target"]).duplicated().mean())
        out[name] = {
            "n": n,
            "exact_duplicate_feature_share": dup,
            "partitioning_features": flags,
            "n_flags": len(flags),
            "n_nontrivial_flags": sum(1 for f in flags if not f["trivial_all_distinct"]),
        }
    return out


# ---------------------------------------------------------------------------
def main():
    rows, pre_registered_commit = load_rows()
    datasets = sorted(_by_dataset(rows))
    result = {
        "analysis": "manuscript figures with no prior producing module (POST-HOC)",
        "post_hoc": True,
        "pre_registered": False,
        "source_pre_registered_commit": pre_registered_commit,
        "delta_g": DELTA_G,
        "n_runs": len(rows),
        "n_datasets": len(datasets),
        "between_dataset_rho": between_dataset_rho(rows),
        "candidate_outcomes": candidate_outcomes(rows),
        "selection_bias": selection_bias(rows),
        "exclusions": exclusions(rows),
        "positives_concentration": positives_concentration(rows),
        "structural_screen": structural_screen(datasets),
    }
    OUT_FILE.write_text(json.dumps(result, indent=1), encoding="utf-8")

    bd = result["between_dataset_rho"]
    print(f"\n  runs {result['n_runs']}  datasets {result['n_datasets']}\n")
    print("  between-dataset rho")
    for k in ("all", "estimable"):
        b = bd[k]
        print(f"    {k:10s} rho {b['rho']:+.4f}  "
              f"[{b['ci_low']:+.3f}, {b['ci_high']:+.3f}]  n={b['n_datasets']}")
    print("\n  candidate outcomes (rho all 25 / estimable)")
    for k, v in result["candidate_outcomes"].items():
        est = v["rho_estimable"]
        print(f"    {k:28s} {v['rho_all_25']:+.4f}  "
              + (f"{est:+.4f}" if est is not None else "   ---"))
    sb = result["selection_bias"]
    print(f"\n  selection bias: slope {sb['automated_slope']:+.4f} "
          f"intercept {sb['automated_intercept']:+.4f} "
          f"predicted {sb['predicted_slope_coefficient']:.5f}")
    print(f"    control own-sigma {sb['control_own_sigma_slope']:+.4f}  "
          f"cross-sigma {sb['control_cross_sigma_slope']:+.4f}  "
          f"CI [{sb['clustered_ci']['ci_low']:+.3f}, {sb['clustered_ci']['ci_high']:+.3f}]")
    ex = result["exclusions"]
    print(f"\n  MLC++ excluded: {ex['mlcpp_boolean_excluded']['rho_remaining_22']:+.4f} all / "
          f"{ex['mlcpp_boolean_excluded']['rho_remaining_estimable']:+.4f} estimable")
    print(f"  jackknife range [{ex['jackknife_range'][0]:+.4f}, {ex['jackknife_range'][1]:+.4f}]  "
          f"most influential {ex['most_influential']['dataset']} "
          f"({ex['most_influential']['delta']:+.4f})")
    pc = result["positives_concentration"]
    w = pc["rho_without_top5"]
    print(f"\n  positives {pc['total_positives']}, {pc['n_datasets_supplying_half']} datasets supply half, "
          f"{pc['n_zero']} supply none")
    print(f"  dropping the top 5: rho_all {w['rho_all']:+.4f} (n={w['n_all']})  "
          f"rho_estimable {w['rho_estimable']:+.4f} (n={w['n_estimable']}) "
          f"[{w['clustered_ci_estimable']['ci_low']:+.3f}, "
          f"{w['clustered_ci_estimable']['ci_high']:+.3f}]")
    ss = result["structural_screen"]
    if "error" not in ss:
        flagged = {k: v for k, v in ss.items() if v.get("n_flags")}
        nontrivial = {k: v for k, v in ss.items() if v.get("n_nontrivial_flags")}
        print(f"\n  structural screen: {len(flagged)} datasets flagged, "
              f"{len(nontrivial)} with a NON-trivial flag")
        for k, v in sorted(nontrivial.items()):
            feats = ", ".join(f"{f['feature']} ({f['distinct_share']:.2f})"
                              for f in v["partitioning_features"]
                              if not f["trivial_all_distinct"])
            print(f"    {k:28s} {feats}")
    print(f"\n  Written: {OUT_FILE}\n")


if __name__ == "__main__":
    main()
