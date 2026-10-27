"""
Post-hoc paired difference re-analysis (written 2026-10-27), closing open item
2 of `docs/review_response_2026-10-22.md`.

**THIS IS NOT PRE-REGISTERED.** `score_stratified.py` reports a separate
dataset-clustered-bootstrap interval for each diagnostic on its own. The
reviewer's point: two separate intervals that both exclude (or both include)
chance do not by themselves say whether diagnostic A outperforms diagnostic B
-- "A's CI is [0.55,0.70] and B's is [0.45,0.65]" is not evidence A beats B,
because the two intervals are computed from the same correlated 9 (or 8)
datasets and the overlap/non-overlap of separately-computed intervals is a
well-known unreliable proxy for a paired comparison. This script computes the
PAIRED difference directly: for every pair of diagnostics, every bootstrap
resample draws one set of datasets and computes BOTH diagnostics' concordance
on that exact resample, then differences them -- so shared resampling noise
cancels out of the difference the same way it would in a paired t-test. No new
pipeline runs; reuses `score_stratified.py`'s extraction, concordance and
dataset-clustered-bootstrap machinery unchanged.

Scope: same three sources as the delta_G sensitivity script and for the same
reason -- study2_B, study2_C, study3_transfer, the sources behind the current
Contribution 1/2 figures. Reported at two stratifications: pooled (what the
published AUROC table compares) and within_dataset (what the granularity
finding in `stratified_reanalysis.md` is actually about -- most pairwise
differences are expected to be noise here, since every diagnostic was already
found to sit at or below chance within dataset).

Usage:
    python -m evaluation.score_diagnostic_differences
"""
import json
from itertools import combinations
from pathlib import Path

from evaluation.score_stratified import (
    DIAGNOSTICS,
    STRATIFICATIONS,
    cluster_bootstrap,
    extract,
    load_runs,
    stratified_concordance,
)

RESULTS_DIR = Path(__file__).resolve().parent / "results"

SOURCES = ["study2_B", "study2_C", "study3_transfer"]
STRATA_REPORTED = ["pooled", "within_dataset"]


def paired_diff_statistic(rows, diag_a, diag_b, keyfn):
    ca = stratified_concordance(rows, diag_a, keyfn)["concordance"]
    cb = stratified_concordance(rows, diag_b, keyfn)["concordance"]
    if ca is None or cb is None:
        return None
    return ca - cb


def analyse_source(source):
    rows = extract(load_runs(source))
    n_datasets = len({r["dataset"] for r in rows})
    pairs = list(combinations(DIAGNOSTICS, 2))
    out = {"source": source, "n_datasets": n_datasets, "strata": {}}
    for sname in STRATA_REPORTED:
        keyfn = STRATIFICATIONS[sname]
        entries = []
        for diag_a, diag_b in pairs:
            point = paired_diff_statistic(rows, diag_a, diag_b, keyfn)
            ca = stratified_concordance(rows, diag_a, keyfn)["concordance"]
            cb = stratified_concordance(rows, diag_b, keyfn)["concordance"]
            ci = cluster_bootstrap(
                rows, lambda rs, a=diag_a, b=diag_b, k=keyfn: paired_diff_statistic(rs, a, b, k)
            )
            excludes_zero = (
                ci["ci_low"] is not None and ci["ci_high"] is not None
                and (ci["ci_low"] > 0 or ci["ci_high"] < 0)
            )
            entries.append(
                {
                    "a": diag_a, "b": diag_b,
                    "concordance_a": ca, "concordance_b": cb,
                    "diff": point,
                    "ci_low": ci["ci_low"], "ci_high": ci["ci_high"],
                    "n_valid_resamples": ci["n_valid_resamples"],
                    "excludes_zero": excludes_zero,
                }
            )
        out["strata"][sname] = entries
    return out


def report(result):
    src = result["source"]
    print(f"\n{'=' * 90}")
    print(f"PAIRED DIFFERENCE RE-ANALYSIS (not pre-registered) -- {src}")
    print(f"{'=' * 90}")
    print(f"{result['n_datasets']} source datasets; dataset-clustered paired bootstrap, "
          "2000 resamples, same resample used for both diagnostics in a pair.")
    for sname in STRATA_REPORTED:
        entries = result["strata"][sname]
        print(f"\n-- {sname} --")
        print(f"  {'A':<20}{'B':<20}{'conc(A)':>9}{'conc(B)':>9}{'diff':>9}{'95% CI':>22}{'excl.0':>8}")
        any_significant = False
        for e in entries:
            if e["diff"] is None:
                diffstr, cistr = "   NA", "        NA"
            else:
                diffstr = f"{e['diff']:+.3f}"
                lo, hi = e["ci_low"], e["ci_high"]
                cistr = "NA" if lo is None else f"[{lo:+.2f},{hi:+.2f}]"
            flag = "yes" if e["excludes_zero"] else "no"
            if e["excludes_zero"]:
                any_significant = True
            ca_str = "NA" if e["concordance_a"] is None else f"{e['concordance_a']:.3f}"
            cb_str = "NA" if e["concordance_b"] is None else f"{e['concordance_b']:.3f}"
            print(
                f"  {e['a']:<20}{e['b']:<20}"
                f"{ca_str:>9}{cb_str:>9}"
                f"{diffstr:>9}{cistr:>22}{flag:>8}"
            )
        if not any_significant:
            print("  -> no pair's difference-in-concordance interval excludes zero at this stratum.")


def main():
    results = {src: analyse_source(src) for src in SOURCES}
    for src in SOURCES:
        report(results[src])
    out = RESULTS_DIR / "diagnostic_difference_scores.json"
    with open(out, "w") as f:
        json.dump(
            {
                "pre_registered": False,
                "label": "post-hoc paired-difference re-analysis, per review_response_2026-10-22.md open item 2",
                "sources": results,
            },
            f,
            indent=2,
        )
    print(f"\nWritten: {out}")


if __name__ == "__main__":
    main()
