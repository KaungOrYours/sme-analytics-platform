"""POST-HOC: how reliably is the outcome measured at run resolution?

THIS IS POST-HOC. Not pre-registered. Re-measures stored runs, adds none.

Why it exists
-------------
The per-run result is reported as UNRESOLVED rather than negative, on the grounds
that the outcome `poor_optimism = (G > delta_G)` is too noisy at run resolution to
separate an absent signal from an unmeasurable one. Every figure supporting that
claim was computed in prose and committed nowhere, which is the same defect class
that put a mis-transcribed correlation into an earlier document. This module emits
all of them to JSON.

What is computed
----------------
A cell is one (dataset, corruption family, rate) combination, containing exactly 3
runs that differ ONLY in the random seed. Within a cell, any variation in `G` is
measurement noise by construction.

  1. Label instability      cells whose 3 seeds disagree on the label.
  2. One-way ICC of G       between-cell variance as a share of the total, by the
                            standard one-way random-effects decomposition. Low ICC
                            means most of G's variation is seed noise.
  3. Variance split         the share of within-cell Var(G) attributable to
                            S_test, which Study 4's repeated-CV estimator did not
                            re-estimate. Reported two ways, because they answer
                            different questions and have been confused before:
                              (a) within-cell: Var(S_test) / Var(G) inside cells
                              (b) seed-only:   the same over the pooled seed-level
                                  deviations, which is the figure the discussion
                                  of Study 4's scope uses.
  4. Sampling SE of S_test  per run, under TWO named estimators, because the
                            previously quoted median did not match either:
                              Hanley-McNeil, and the binormal approximation
                              sqrt(A(1-A)/min(n_pos, n_neg)).
                            Reported separately rather than reconciled, so the
                            paper can name which it means.
  5. AUROC quantum          runs where the smallest possible change in S_test,
                            1/(n_pos * n_neg), is itself at least delta_G. On
                            those runs the label cannot be finer than the grid.
  6. Cohen's kappa          label test-retest agreement across seeds, over all
                            within-cell seed pairs.
  7. THE ORACLE CEILING     the headline number, and the one that most needs a
                            definition because it decides whether the per-run
                            result is "unresolved" or "negative".

The oracle, stated precisely
----------------------------
A predictor that knows the systematic component of `G` as well as the design
permits, and nothing else. For each run we take the mean `G` of the OTHER two
seeds in its own cell -- leave-one-seed-out -- and use that as the score. It has
perfect knowledge of the cell (dataset, family, rate) and no knowledge of the
run's own seed draw, which is exactly the information a diagnostic computed from
the training partition could in principle carry.

Scored by the project's own within-dataset `stratified_concordance` against the
run's own stored label, over the same strata as every other concordance figure, so
it is directly comparable with the diagnostic's.

This is a CEILING, not a bound in the formal sense: a predictor with extra
information about a specific seed could beat it. It answers "how well could
anything that knows only the cell do against this label", which is the question
the unresolved framing turns on.

Reads only. Writes results/outcome_reliability_scores.json.

Run from the REPO ROOT:
    backend/venv/bin/python3 -m evaluation.score_outcome_reliability
"""

from __future__ import annotations

import json
import statistics as st
from pathlib import Path

from evaluation.score_stratified import (
    BOOTSTRAP_SEED,
    DIAGNOSTICS,
    RESULTS_DIR,
    cluster_bootstrap,
    stratified_concordance,
)

GROUP_FILES = ("study2_group_A_results.json",
               "study2_group_B_results.json",
               "study2_group_C_results.json")
OUTPUT_FILE = "outcome_reliability_scores.json"

DELTA_G = 0.05
LABEL = "poor_optimism"

DIAGNOSTICS.setdefault("oracle_loso", True)

WITHIN_DATASET = lambda row: row["dataset"]  # noqa: E731


def load_runs():
    rows = []
    for filename in GROUP_FILES:
        path = RESULTS_DIR / filename
        if not path.exists():
            raise SystemExit(f"{path} not found.")
        with path.open() as fh:
            payload = json.load(fh)
        for record in payload["runs"]:
            a = record.get("automated")
            if not a:
                continue
            # Row-level labels are present in the local run records and absent
            # from the redistributable export, which stores the counts instead
            # (see export_public_results.py). Only the counts are ever used, so
            # this module reproduces identically from either.
            y = a.get("y_test") or []
            if y:
                codes = sorted(set(y))
                n_pos = sum(1 for v in y if v == codes[-1]) if len(codes) == 2 else 0
                n_neg = len(y) - n_pos if len(codes) == 2 else 0
            else:
                n_pos = a.get("n_test_pos", 0)
                n_neg = a.get("n_test_neg", 0)
            rows.append({
                "dataset": record["dataset"],
                "family": record["corruption_type"],
                "rate": record["rate"],
                "seed": record["seed"],
                "G": a["G"],
                "s_cv": a["s_cv_selected"],
                "s_test": a["s_test"],
                "n_pos": n_pos,
                "n_neg": n_neg,
                "poor": bool(a["labels"][LABEL]),
            })
    return rows


def cells(rows):
    out = {}
    for row in rows:
        out.setdefault((row["dataset"], row["family"], row["rate"]), []).append(row)
    return out


# --- 1, 6: label instability and kappa -------------------------------------
def label_stability(by_cell):
    total = split = with_positive = split_with_positive = 0
    agree = pairs = 0
    both_pos = 0
    for group in by_cell.values():
        labels = [r["poor"] for r in group]
        total += 1
        has_pos = any(labels)
        if has_pos:
            with_positive += 1
        if len(set(labels)) > 1:
            split += 1
            if has_pos:
                split_with_positive += 1
        for i in range(len(labels)):
            for j in range(i + 1, len(labels)):
                pairs += 1
                if labels[i] == labels[j]:
                    agree += 1
                if labels[i] and labels[j]:
                    both_pos += 1
    observed = agree / pairs if pairs else None
    # Chance agreement at the observed marginal base rate.
    p = sum(1 for g in by_cell.values() for r in g if r["poor"]) / sum(
        len(g) for g in by_cell.values())
    chance = p * p + (1 - p) * (1 - p)
    kappa = (observed - chance) / (1 - chance) if observed is not None and chance < 1 else None
    return {
        "n_cells": total,
        "n_cells_split_by_seed": split,
        "n_cells_with_a_positive": with_positive,
        "n_positive_cells_split_by_seed": split_with_positive,
        "share_of_positive_cells_split": (
            split_with_positive / with_positive if with_positive else None),
        "base_rate": p,
        "observed_agreement": observed,
        "chance_agreement": chance,
        "cohens_kappa": kappa,
        "n_seed_pairs": pairs,
    }


# --- 2, 3: variance decomposition ------------------------------------------
def variance_components(by_cell):
    cell_means, within_ss, within_n = [], 0.0, 0
    sd_within = []
    dev_g, dev_cv, dev_test = [], [], []
    for group in by_cell.values():
        if len(group) < 2:
            continue
        gs = [r["G"] for r in group]
        m = st.mean(gs)
        cell_means.append(m)
        within_ss += sum((g - m) ** 2 for g in gs)
        within_n += len(gs) - 1
        sd_within.append(st.stdev(gs))
        mcv, mtest = st.mean(r["s_cv"] for r in group), st.mean(r["s_test"] for r in group)
        for r in group:
            dev_g.append(r["G"] - m)
            dev_cv.append(r["s_cv"] - mcv)
            dev_test.append(r["s_test"] - mtest)

    var_within = within_ss / within_n if within_n else None
    var_between = st.variance(cell_means) if len(cell_means) > 1 else None
    icc = (var_between / (var_between + var_within)
           if var_between is not None and var_within else None)

    def var(xs):
        return sum(v * v for v in xs) / (len(xs) - 1) if len(xs) > 1 else None

    v_g, v_cv, v_test = var(dev_g), var(dev_cv), var(dev_test)
    return {
        "n_cells_used": len(cell_means),
        "var_within_cell_G": var_within,
        "var_between_cell_G": var_between,
        "icc_one_way": icc,
        "pooled_within_cell_sd_G": (var_within ** 0.5 if var_within else None),
        "median_within_cell_sd_G": st.median(sd_within) if sd_within else None,
        "share_cells_sd_above_delta_g": (
            sum(1 for s in sd_within if s > DELTA_G) / len(sd_within) if sd_within else None),
        "seed_deviation_var_G": v_g,
        "seed_deviation_var_s_cv": v_cv,
        "seed_deviation_var_s_test": v_test,
        "share_of_G_variance_from_s_test_within_cell": (
            v_test / v_g if v_g else None),
    }


# --- 4, 5: sampling error of a single test-set AUROC -----------------------
def test_score_precision(rows):
    hanley, binormal, quantum_hits, n_test = [], [], 0, []
    for r in rows:
        a, npos, nneg = r["s_test"], r["n_pos"], r["n_neg"]
        n_test.append(npos + nneg)
        if npos == 0 or nneg == 0:
            continue
        if npos * nneg > 0 and 1.0 / (npos * nneg) >= DELTA_G:
            quantum_hits += 1
        q1 = a / (2 - a) if (2 - a) else 0
        q2 = 2 * a * a / (1 + a) if (1 + a) else 0
        var = (a * (1 - a) + (npos - 1) * (q1 - a * a) + (nneg - 1) * (q2 - a * a)) / (npos * nneg)
        if var > 0:
            hanley.append(var ** 0.5)
        b = (a * (1 - a) / min(npos, nneg)) ** 0.5
        binormal.append(b)
    return {
        "n_runs": len(rows),
        "median_n_test": st.median(n_test),
        "min_n_test": min(n_test),
        "max_n_test": max(n_test),
        "hanley_mcneil": {
            "median_se": st.median(hanley) if hanley else None,
            "n_runs_se_above_delta_g": sum(1 for v in hanley if v > DELTA_G),
            "n_scored": len(hanley),
        },
        "binormal_approximation": {
            "median_se": st.median(binormal) if binormal else None,
            "n_runs_se_above_delta_g": sum(1 for v in binormal if v > DELTA_G),
            "n_scored": len(binormal),
        },
        "n_runs_auroc_quantum_at_or_above_delta_g": quantum_hits,
        "delta_g": DELTA_G,
    }


# --- 7: the oracle ---------------------------------------------------------
def oracle_ceiling(by_cell):
    """Leave-one-seed-out cell-mean G as the predictor. See module docstring."""
    scored = []
    for group in by_cell.values():
        if len(group) < 2:
            continue
        total = sum(r["G"] for r in group)
        for r in group:
            others = (total - r["G"]) / (len(group) - 1)
            scored.append({
                "dataset": r["dataset"],
                "family": r["family"],
                "rate": r["rate"],
                "poor": r["poor"],
                "values": {"oracle_loso": others},
            })
    # Leaky upper reference: the FULL cell mean, which includes the run's own G.
    # It cannot be attained by any honest predictor, but the gap between it and the
    # leave-one-out oracle is the oracle's own estimation error at three seeds --
    # i.e. how much of the ceiling is a design parameter rather than a property of
    # the measurement problem. Reported so the reader can separate the two.
    leaky = []
    for group in by_cell.values():
        if len(group) < 2:
            continue
        m = sum(r["G"] for r in group) / len(group)
        for r in group:
            leaky.append({"dataset": r["dataset"], "family": r["family"],
                          "rate": r["rate"], "poor": r["poor"],
                          "values": {"oracle_loso": m}})
    leaky_conc = stratified_concordance(leaky, "oracle_loso", WITHIN_DATASET)["concordance"]

    observed = stratified_concordance(scored, "oracle_loso", WITHIN_DATASET)
    ci = cluster_bootstrap(
        scored,
        lambda sample: stratified_concordance(
            sample, "oracle_loso", WITHIN_DATASET)["concordance"],
    )
    return {
        "definition": (
            "mean G of the other seeds in the same (dataset, family, rate) cell, "
            "scored by within-dataset stratified concordance against the run's own "
            "stored label"
        ),
        "concordance": observed["concordance"],
        "n_pairs": observed.get("n_pairs"),
        "n_strata_used": observed.get("n_strata_used"),
        "ci_low": ci.get("ci_low"),
        "ci_high": ci.get("ci_high"),
        "n_runs_scored": len(scored),
        "full_cell_mean_reference": leaky_conc,
        "full_cell_mean_note": (
            "leaky upper reference including the run's own G; the gap to the "
            "leave-one-out oracle is the oracle's estimation error at three seeds"
        ),
    }


def fmt(v, w=8):
    return "     n/a" if v is None else f"{v:{w}.4f}"


def main():
    rows = load_runs()
    by_cell = cells(rows)

    result = {
        "analysis": "reliability of the run-level outcome (POST-HOC)",
        "post_hoc": True,
        "pre_registered": False,
        "label": LABEL,
        "delta_g": DELTA_G,
        "n_runs": len(rows),
        "n_datasets": len({r["dataset"] for r in rows}),
        "bootstrap_seed": BOOTSTRAP_SEED,
        "label_stability": label_stability(by_cell),
        "variance_components": variance_components(by_cell),
        "test_score_precision": test_score_precision(rows),
        "oracle": oracle_ceiling(by_cell),
    }

    ls, vc, tp, orc = (result["label_stability"], result["variance_components"],
                       result["test_score_precision"], result["oracle"])
    print()
    print(f"OUTCOME RELIABILITY AT RUN RESOLUTION -- {len(rows)} runs, "
          f"{result['n_datasets']} datasets, delta_G = {DELTA_G}")
    print()
    print(f"  cells (dataset x family x rate), 3 seeds each        {ls['n_cells']}")
    print(f"  cells containing a positive                          {ls['n_cells_with_a_positive']}")
    print(f"  ... of those, split by the seed alone                "
          f"{ls['n_positive_cells_split_by_seed']} "
          f"({ls['share_of_positive_cells_split']:.1%})")
    print(f"  one-way ICC of G across seeds                       {fmt(vc['icc_one_way'])}")
    print(f"  pooled within-cell SD of G                          {fmt(vc['pooled_within_cell_sd_G'])}"
          f"   ({vc['share_cells_sd_above_delta_g']:.1%} of cells above delta_G)")
    print(f"  share of within-cell Var(G) from S_test             "
          f"{vc['share_of_G_variance_from_s_test_within_cell']:.1%}")
    print(f"  label test-retest agreement (kappa)                 {fmt(ls['cohens_kappa'])}")
    print()
    print(f"  test partition size: median {tp['median_n_test']:.0f}, "
          f"range {tp['min_n_test']}-{tp['max_n_test']}")
    for key, label in (("hanley_mcneil", "Hanley-McNeil"),
                       ("binormal_approximation", "binormal approx")):
        e = tp[key]
        print(f"    {label:<16} median SE {fmt(e['median_se'])}   "
              f"{e['n_runs_se_above_delta_g']}/{e['n_scored']} runs with SE > delta_G")
    print(f"    runs where the AUROC quantum alone is >= delta_G: "
          f"{tp['n_runs_auroc_quantum_at_or_above_delta_g']}")
    print()
    print(f"  ORACLE CEILING (leave-one-seed-out cell mean)       {fmt(orc['concordance'])}"
          f"   CI [{fmt(orc['ci_low'],5)},{fmt(orc['ci_high'],5)}]")
    print(f"    {orc['n_pairs']} pairs over {orc['n_strata_used']} strata")
    print(f"  full-cell-mean reference (leaky, 3-seed budget)     {fmt(orc['full_cell_mean_reference'])}")
    print()
    print("  The ceiling is what a predictor knowing the cell but not the seed can")
    print("  reach against this label. Compare any diagnostic against it, not 0.5.")
    print()

    out = RESULTS_DIR / OUTPUT_FILE
    with out.open("w") as fh:
        json.dump(result, fh, indent=2)
    print(f"Written: {out}")


if __name__ == "__main__":
    main()
