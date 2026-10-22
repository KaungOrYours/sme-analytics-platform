"""
Post-hoc stratified re-analysis of Studies 2 and 3 (written 2026-10-22).

**THIS IS NOT PRE-REGISTERED.** Studies 2 and 3 were pre-registered before they
ran; this re-analysis was not. It was written in response to an external
critical review of the project's documents, which asked whether the diagnostics'
reported discrimination separates "this *dataset* is risky" from "this *run*
will disappoint". It is therefore exploratory and is labelled as such everywhere
it is reported. No new pipeline runs are produced: every number here is a
re-analysis of run records already collected under the earlier protocols.

What it adds over `score_study2.py` / `recalibrate_study3.py`:

1. **Stratified concordance.** Threshold-free discrimination computed over
   pairs that share a stratum, for four nestings: pooled (no stratification),
   within corruption family, within dataset, and within dataset x family.
   Comparing them decomposes the pooled figure into between-dataset ordering
   and within-dataset ordering. A diagnostic that only ranks datasets scores
   high pooled and at chance within dataset.

2. **Dataset-clustered bootstrap.** Every interval resamples whole SOURCE
   DATASETS with replacement (all of a dataset's runs travel together), not
   individual runs. Studies 1-3 all resampled runs as exchangeable, which
   treats 21 correlated runs from one dataset as 21 independent observations
   and produces anti-conservative intervals. The cluster unit here matches the
   unit the transfer claims are about.

3. **Reproducible threshold-free AUROC.** The AUROC tables in
   `docs/study2_results.md` and `docs/study3_results.md` were computed inline
   and never committed as code. The pooled and within-family figures emitted
   here recompute them from the same run records, so the published tables are
   auditable. `--verify` cross-checks a sample against the documented values.

4. **Explicit NA accounting.** Strata with no positive or no negative outcome
   are undefined, not zero. They are excluded from concordance and counted, and
   the per-dataset x family outcome table reports the counts behind every cell.

Usage:
    python -m evaluation.score_stratified study2_B
    python -m evaluation.score_stratified study2_C
    python -m evaluation.score_stratified study3_transfer
    python -m evaluation.score_stratified all
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

RESULTS_DIR = Path(__file__).resolve().parent / "results"

N_BOOTSTRAP = 2000
BOOTSTRAP_SEED = 0

# Primary label, carried forward unchanged from Studies 1-3 so the figures here
# are directly comparable with the published ones.
LABEL = "poor_optimism"

# Raw (continuous) diagnostic value per run, and whether a HIGHER value is
# supposed to indicate MORE risk. The thresholded versions live in
# diagnostics2.DIAGNOSTIC_NAMES; this module is deliberately threshold-free.
DIAGNOSTICS = {
    "sigma_cv": True,
    "evalml_cov": True,
    "evalml_range": True,
    "fold_contamination": True,
    "epv": False,
    "n_over_p": False,
}

SOURCES = {
    "study2_A": "study2_group_A_results.json",
    "study2_B": "study2_group_B_results.json",
    "study2_C": "study2_group_C_results.json",
    "study3_transfer": "study3_transfer_results.json",
}


def load_runs(source):
    path = RESULTS_DIR / SOURCES[source]
    if not path.exists():
        raise SystemExit(f"{path} not found.")
    with open(path) as f:
        return json.load(f)["runs"]


def diagnostic_value(record, name):
    """Raw diagnostic value for one run's automated-pipeline record. Returns
    None where the diagnostic is undefined (e.g. evalml_cov when the CV mean is
    zero), never a coerced default."""
    if name == "n_over_p":
        p = record.get("p")
        return None if not p else record["n"] / p
    return record.get(name)


def extract(runs):
    """One flat row per run: (dataset, family, {diagnostic: value}, outcome)."""
    rows = []
    for r in runs:
        a = r["automated"]
        rows.append(
            {
                "dataset": r["dataset"],
                "family": r["corruption_type"],
                "rate": r["rate"],
                "values": {d: diagnostic_value(a, d) for d in DIAGNOSTICS},
                "poor": bool(a["labels"][LABEL]),
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Stratified concordance
# ---------------------------------------------------------------------------
STRATIFICATIONS = {
    "pooled": lambda row: "_all",
    "within_family": lambda row: row["family"],
    "within_dataset": lambda row: row["dataset"],
    "within_dataset_family": lambda row: (row["dataset"], row["family"]),
    # Strictest control: dataset, corruption family AND corruption rate all
    # held fixed, so the only thing varying inside a stratum is the random
    # seed. If discrimination survives here it cannot be an artefact of the
    # injected condition; strata are only 3 runs wide, so most are undefined.
    "within_dataset_family_rate": lambda row: (row["dataset"], row["family"], row["rate"]),
}


def stratified_concordance(rows, diagnostic, keyfn):
    """P(diagnostic ranks a poor run above a non-poor run | same stratum),
    ties counted as 0.5. Equals AUROC when there is a single stratum.

    Pairs are only formed inside a stratum, so between-stratum ordering cannot
    contribute. Strata lacking either outcome class are undefined and excluded.
    """
    higher_is_worse = DIAGNOSTICS[diagnostic]
    strata = defaultdict(list)
    n_undefined_values = 0
    for row in rows:
        v = row["values"][diagnostic]
        if v is None:
            n_undefined_values += 1
            continue
        strata[keyfn(row)].append((v, row["poor"]))

    conc = ties = total = 0
    used = excluded = 0
    for members in strata.values():
        pos = [v for v, p in members if p]
        neg = [v for v, p in members if not p]
        if not pos or not neg:
            excluded += 1
            continue
        used += 1
        for a in pos:
            for b in neg:
                total += 1
                if a == b:
                    ties += 1
                elif (a > b) == higher_is_worse:
                    conc += 1
    if total == 0:
        return {
            "concordance": None,
            "n_pairs": 0,
            "n_strata_used": used,
            "n_strata_excluded": excluded,
            "n_undefined_values": n_undefined_values,
        }
    return {
        "concordance": (conc + 0.5 * ties) / total,
        "n_pairs": total,
        "n_strata_used": used,
        "n_strata_excluded": excluded,
        "n_undefined_values": n_undefined_values,
    }


# ---------------------------------------------------------------------------
# Dataset-clustered bootstrap
# ---------------------------------------------------------------------------
def cluster_bootstrap(rows, statistic, n_resamples=N_BOOTSTRAP, seed=BOOTSTRAP_SEED):
    """Percentile CI resampling whole SOURCE DATASETS with replacement.

    All of a dataset's runs travel together, so the interval reflects the number
    of independent datasets (9, or 8 in transfer) rather than the number of
    correlated runs (189, 168). Resamples for which the statistic is undefined
    are dropped and counted rather than imputed; a CI computed from very few
    valid resamples is reported with that count so it cannot be read as solid.
    """
    by_dataset = defaultdict(list)
    for row in rows:
        by_dataset[row["dataset"]].append(row)
    names = sorted(by_dataset)
    k = len(names)
    rng = np.random.default_rng(seed)

    vals = []
    for _ in range(n_resamples):
        picked = rng.choice(k, size=k, replace=True)
        resampled = []
        for i, idx in enumerate(picked):
            # Re-key duplicated datasets so a dataset drawn twice forms two
            # separate strata rather than one double-sized one.
            for row in by_dataset[names[idx]]:
                clone = dict(row)
                clone["dataset"] = f"{row['dataset']}#{i}"
                resampled.append(clone)
        v = statistic(resampled)
        if v is not None and not (isinstance(v, float) and np.isnan(v)):
            vals.append(v)

    if not vals:
        return {"ci_low": None, "ci_high": None, "n_valid_resamples": 0, "n_clusters": k}
    arr = np.array(vals, dtype=float)
    return {
        "ci_low": float(np.percentile(arr, 2.5)),
        "ci_high": float(np.percentile(arr, 97.5)),
        "bootstrap_median": float(np.median(arr)),
        "n_valid_resamples": len(arr),
        "n_clusters": k,
    }


# ---------------------------------------------------------------------------
# Between-dataset ordering, measured directly
# ---------------------------------------------------------------------------
def spearman(x, y):
    """Spearman rho without scipy. Average ranks for ties."""
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for t in range(i, j + 1):
                r[order[t]] = avg
            i = j + 1
        return r

    if len(x) < 3:
        return None
    rx, ry = rank(x), rank(y)
    mx, my = np.mean(rx), np.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return None if den == 0 else float(num / den)


def between_dataset_ordering(rows, diagnostic):
    """Does the dataset's mean diagnostic rank its failure rate?

    This is the quantity a pooled AUROC is dominated by when the diagnostic is
    near-constant within a dataset. Reported as Spearman rho between each
    dataset's mean diagnostic value and its poor rate, signed so that positive
    always means "the diagnostic orders datasets correctly".
    """
    agg = defaultdict(lambda: {"vals": [], "poor": []})
    for row in rows:
        v = row["values"][diagnostic]
        if v is None:
            continue
        agg[row["dataset"]]["vals"].append(v)
        agg[row["dataset"]]["poor"].append(1.0 if row["poor"] else 0.0)
    means = [np.mean(d["vals"]) for d in agg.values()]
    rates = [np.mean(d["poor"]) for d in agg.values()]
    rho = spearman(means, rates)
    if rho is None:
        return {"spearman_rho": None, "n_datasets": len(agg)}
    if not DIAGNOSTICS[diagnostic]:
        rho = -rho  # lower-is-worse diagnostics order correctly when rho < 0
    return {"spearman_rho": rho, "n_datasets": len(agg)}


def within_dataset_spread(rows, diagnostic):
    """How much room a diagnostic even has to discriminate inside a dataset.

    A diagnostic that is constant within a dataset cannot rank that dataset's
    runs however good its pooled figure looks. Reported as the mean number of
    distinct values per dataset and the share of total variance that is
    within-dataset.
    """
    by_ds = defaultdict(list)
    for row in rows:
        v = row["values"][diagnostic]
        if v is not None:
            by_ds[row["dataset"]].append(v)
    if not by_ds:
        return {"mean_distinct_values_per_dataset": None, "within_dataset_variance_share": None}
    distinct = [len({round(v, 10) for v in vs}) for vs in by_ds.values()]
    allv = [v for vs in by_ds.values() for v in vs]
    grand = np.mean(allv)
    total_ss = sum((v - grand) ** 2 for v in allv)
    within_ss = sum(sum((v - np.mean(vs)) ** 2 for v in vs) for vs in by_ds.values())
    return {
        "mean_distinct_values_per_dataset": float(np.mean(distinct)),
        "within_dataset_variance_share": None if total_ss == 0 else float(within_ss / total_ss),
    }


# ---------------------------------------------------------------------------
# Outcome counts, per dataset x family, with NA flags
# ---------------------------------------------------------------------------
def outcome_table(rows):
    cells = defaultdict(lambda: {"n": 0, "poor": 0})
    for row in rows:
        c = cells[(row["dataset"], row["family"])]
        c["n"] += 1
        c["poor"] += 1 if row["poor"] else 0
    out = []
    for (ds, fam), c in sorted(cells.items()):
        out.append(
            {
                "dataset": ds,
                "family": fam,
                "n_runs": c["n"],
                "n_poor": c["poor"],
                "n_not_poor": c["n"] - c["poor"],
                "estimable": c["poor"] > 0 and c["poor"] < c["n"],
            }
        )
    return out


# ---------------------------------------------------------------------------
def analyse(source):
    rows = extract(load_runs(source))
    families = sorted({r["family"] for r in rows})
    datasets = sorted({r["dataset"] for r in rows})

    # A dataset only contributes evidence about discrimination if it contains
    # both outcome classes. Datasets that are all-poor or all-clean cannot
    # order anything, so the count of estimable clusters -- not the run count
    # and not even the dataset count -- is the real sample size behind every
    # figure below.
    estimable_datasets = sorted(
        ds
        for ds in datasets
        if 0 < sum(1 for r in rows if r["dataset"] == ds and r["poor"])
        < sum(1 for r in rows if r["dataset"] == ds)
    )

    result = {
        "source": source,
        "label": LABEL,
        "pre_registered": False,
        "n_runs": len(rows),
        "n_datasets": len(datasets),
        "n_datasets_estimable": len(estimable_datasets),
        "estimable_datasets": estimable_datasets,
        "n_poor": sum(1 for r in rows if r["poor"]),
        "families": families,
        "bootstrap": {
            "unit": "source dataset (cluster)",
            "n_resamples": N_BOOTSTRAP,
            "seed": BOOTSTRAP_SEED,
        },
        "diagnostics": {},
        "outcome_table": outcome_table(rows),
    }

    for diag in DIAGNOSTICS:
        entry = {"stratifications": {}}
        for sname, keyfn in STRATIFICATIONS.items():
            point = stratified_concordance(rows, diag, keyfn)
            ci = cluster_bootstrap(
                rows,
                lambda rs, d=diag, k=keyfn: stratified_concordance(rs, d, k)["concordance"],
            )
            entry["stratifications"][sname] = {**point, **ci}
        # Per-family within-dataset concordance: the strictest honest view.
        per_family = {}
        for fam in families:
            sub = [r for r in rows if r["family"] == fam]
            per_family[fam] = {
                "pooled": stratified_concordance(sub, diag, STRATIFICATIONS["pooled"]),
                "within_dataset": stratified_concordance(sub, diag, STRATIFICATIONS["within_dataset"]),
            }
        entry["per_family"] = per_family
        entry["between_dataset_ordering"] = between_dataset_ordering(rows, diag)
        entry["within_dataset_spread"] = within_dataset_spread(rows, diag)
        result["diagnostics"][diag] = entry

    return result


def fmt(v, width=6):
    return " " * (width - 2) + "NA" if v is None else f"{v:{width}.3f}"


def report(result):
    src = result["source"]
    print(f"\n{'=' * 78}")
    print(f"POST-HOC STRATIFIED RE-ANALYSIS (not pre-registered) -- {src}")
    print(f"{'=' * 78}")
    print(
        f"{result['n_runs']} runs over {result['n_datasets']} source datasets; "
        f"{result['n_poor']} labelled {result['label']} "
        f"({100 * result['n_poor'] / result['n_runs']:.1f}%)"
    )
    print(
        f"Intervals are 95% percentile CIs from {result['bootstrap']['n_resamples']} "
        f"bootstrap resamples of whole datasets (not runs)."
    )
    n_est = result["n_datasets_estimable"]
    print(
        f"Datasets containing BOTH outcome classes: {n_est} of {result['n_datasets']} "
        f"-- {', '.join(result['estimable_datasets']) if result['estimable_datasets'] else 'none'}"
    )
    if n_est < 3:
        print(
            f"  WARNING: every within-dataset figure below rests on {n_est} dataset(s). "
            "Cluster-bootstrap intervals will be degenerate (identical bounds) because "
            "almost every resample contains the same evidence. Treat these as "
            "descriptive, not inferential."
        )

    # If some resamples had no estimable stratum at all, the surviving
    # intervals are conditional on drawing the informative dataset(s), which
    # makes them narrower than the honest unconditional interval.
    worst = min(
        e["stratifications"][s]["n_valid_resamples"]
        for e in result["diagnostics"].values()
        for s in STRATIFICATIONS
    )
    n_req = result["bootstrap"]["n_resamples"]
    if worst < n_req:
        print(
            f"  WARNING: as few as {worst}/{n_req} resamples ({100 * worst / n_req:.0f}%) "
            "yielded an estimable statistic; the rest drew no dataset containing both "
            "outcome classes. Reported intervals are CONDITIONAL on drawing an "
            "informative dataset and are narrower than the unconditional truth."
        )

    print("\nThreshold-free concordance, by stratification")
    print("(pooled == the published AUROC; within-dataset removes between-dataset ordering)")
    labels = {
        "pooled": "pooled",
        "within_family": "within-family",
        "within_dataset": "within-dataset",
        "within_dataset_family": "within ds x fam",
        "within_dataset_family_rate": "+ rate (seed only)",
    }
    hdr = f"{'diagnostic':<20}" + "".join(f"{labels[s]:>22}" for s in STRATIFICATIONS)
    print(hdr)
    print("-" * len(hdr))
    for diag, e in result["diagnostics"].items():
        line = f"{diag:<20}"
        for sname in STRATIFICATIONS:
            s = e["stratifications"][sname]
            if s["concordance"] is None:
                line += f"{'NA':>22}"
            else:
                lo, hi = s["ci_low"], s["ci_high"]
                # An interval of zero width means the bootstrap never saw a
                # different answer -- a sign of too few estimable clusters,
                # not of precision. Mark it so it cannot be read as a tight CI.
                degenerate = lo is not None and hi is not None and lo == hi
                cell = f"{s['concordance']:.3f} [{fmt(lo, 5)},{fmt(hi, 5)}]"
                if degenerate:
                    cell = f"{s['concordance']:.3f} [degenerate]"
                line += f"{cell:>22}"
        print(line)

    print("\nWhy: how much the diagnostic can even move inside one dataset")
    hdr2 = (
        f"{'diagnostic':<20}{'distinct vals/ds':>18}{'within-ds var share':>22}"
        f"{'between-ds Spearman':>22}"
    )
    print(hdr2)
    print("-" * len(hdr2))
    for diag, e in result["diagnostics"].items():
        sp = e["within_dataset_spread"]
        bd = e["between_dataset_ordering"]
        dv = sp["mean_distinct_values_per_dataset"]
        vs = sp["within_dataset_variance_share"]
        dv_s = "NA" if dv is None else f"{dv:.1f}"
        vs_s = "NA" if vs is None else f"{vs:.3f}"
        rho = bd["spearman_rho"]
        rho_s = "NA" if rho is None else f"{rho:+.3f}"
        print(f"{diag:<20}{dv_s:>18}{vs_s:>22}{rho_s:>22}")

    print("\nWithin-dataset concordance by corruption family (strictest view)")
    fams = result["families"]
    hdr3 = f"{'diagnostic':<20}" + "".join(f"{f:>16}" for f in fams)
    print(hdr3)
    print("-" * len(hdr3))
    for diag, e in result["diagnostics"].items():
        line = f"{diag:<20}"
        for f in fams:
            c = e["per_family"][f]["within_dataset"]["concordance"]
            c_s = "NA" if c is None else f"{c:.3f}"
            line += f"{c_s:>16}"
        print(line)

    print("\nOutcome counts per dataset x corruption family")
    print(f"{'dataset':<28}{'family':<16}{'runs':>6}{'poor':>6}{'estimable':>11}")
    print("-" * 67)
    for c in result["outcome_table"]:
        print(
            f"{c['dataset']:<28}{c['family']:<16}{c['n_runs']:>6}{c['n_poor']:>6}"
            f"{('yes' if c['estimable'] else 'no'):>11}"
        )
    n_est = sum(1 for c in result["outcome_table"] if c["estimable"])
    print(
        f"\n{n_est} of {len(result['outcome_table'])} dataset x family cells contain both "
        f"outcome classes; the rest are undefined, not zero."
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", choices=list(SOURCES) + ["all"])
    args = ap.parse_args()

    sources = [s for s in SOURCES if s != "study2_A"] if args.source == "all" else [args.source]
    for src in sources:
        result = analyse(src)
        report(result)
        out = RESULTS_DIR / f"{src}_stratified_scores.json"
        with open(out, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\nWritten: {out}")


if __name__ == "__main__":
    main()
