"""
Study 4 scorer (docs/study4_protocol.md Section 7).

The protocol commits to scoring with `evaluation/score_stratified.py` UNCHANGED.
This module therefore does not edit that file: it registers Study 4's results
file and estimator list on the imported module at runtime and calls its
`analyse` verbatim. Keeping `score_stratified.py` byte-identical also preserves
the validation that blessed it -- it reproduced all 48 published Study 2/3
AUROC figures exactly before being trusted.

Two analyses, kept separate because they use different outcomes:

  RQ10 (primary, frozen outcome)  concordance of sigma_R1 / R10 / R20 /
                                  pooled20 against Study 2's frozen
                                  poor_optimism label.
  RQ11 (secondary, EXPLORATORY)   concordance of sigma_even against a
                                  RECOMPUTED label from G_decoupled, which
                                  shares no fold scores with sigma_even.

    python -m evaluation.score_study4
"""
import json
from pathlib import Path

import numpy as np

from evaluation import backend_path  # noqa: F401
from evaluation import score_stratified as ss

RESULTS = Path(ss.RESULTS_DIR)
SOURCE_FILE = "study4_estimators_results.json"
ESTIMATORS = ["sigma_R1", "sigma_R10", "sigma_R20", "sigma_pooled20"]
DELTA_G = 0.05


def register():
    """Point score_stratified at Study 4's file and estimators, at runtime."""
    ss.SOURCES["study4"] = SOURCE_FILE
    ss.DIAGNOSTICS = {e: True for e in ESTIMATORS}


def load():
    with open(RESULTS / SOURCE_FILE) as f:
        return json.load(f)


def precision_check(runs):
    """Protocol Section 9: if the extra repeats changed nothing measurable, the
    comparison has no power to separate P11 from P12, and that is the finding."""
    a = np.array([r["automated"]["sigma_R1"] for r in runs], dtype=float)
    b = np.array([r["automated"]["sigma_R20"] for r in runs], dtype=float)
    ok = ~(np.isnan(a) | np.isnan(b))
    a, b = a[ok], b[ok]
    corr = float(np.corrcoef(a, b)[0, 1]) if a.size > 2 else float("nan")
    return {
        "n": int(a.size),
        "pearson_r1_vs_r20": corr,
        "mean_sigma_R1": float(a.mean()),
        "mean_sigma_R20": float(b.mean()),
        "mean_abs_diff": float(np.abs(a - b).mean()),
        "no_power_if_above": 0.95,
        "verdict": ("NO POWER: R20 is nearly identical to R1"
                    if corr > 0.95 else
                    "estimators differ enough to compare"),
    }


def rq11(runs):
    """Decoupled probe. sigma_even and G_decoupled share no fold scores."""
    rows = []
    for r in runs:
        a = r["automated"]
        if a.get("sigma_even") is None or a.get("G_decoupled") is None:
            continue
        rows.append({
            "dataset": r["dataset"],
            "family": r["corruption_type"],
            "rate": r["rate"],
            "values": {"sigma_even": a["sigma_even"]},
            "poor": bool(a["G_decoupled"] > DELTA_G),
        })
    # Scoped registration: stratified_concordance reads the direction from
    # DIAGNOSTICS. Restored in the finally block below so analyse()'s output is
    # unaffected -- RQ11 uses a recomputed outcome and must stay separate.
    saved = ss.DIAGNOSTICS
    ss.DIAGNOSTICS = {"sigma_even": True}
    out = {
        "label": f"RECOMPUTED poor from G_decoupled > {DELTA_G}",
        "exploratory": True,
        "n_runs": len(rows),
        "n_poor": sum(1 for r in rows if r["poor"]),
        "stratifications": {},
    }
    try:
        for sname, keyfn in ss.STRATIFICATIONS.items():
            point = ss.stratified_concordance(rows, "sigma_even", keyfn)
            ci = ss.cluster_bootstrap(
                rows, lambda rs, k=keyfn: ss.stratified_concordance(rs, "sigma_even", k)["concordance"]
            )
            out["stratifications"][sname] = {**point, **ci}
    finally:
        ss.DIAGNOSTICS = saved
    return out


def main():
    register()
    payload = load()
    runs = payload["runs"]

    print(f"Study 4 -- {len(runs)} runs, protocol {payload['protocol']}, "
          f"pre-registered in {payload['pre_registered_commit']}")
    print(f"Validation gate as run: {payload['validation_gate']}")

    pc = precision_check(runs)
    print("\n=== Protocol Section 9 precision check ===")
    print(f"  mean sigma_R1 {pc['mean_sigma_R1']:.4f}   mean sigma_R20 {pc['mean_sigma_R20']:.4f}"
          f"   mean|diff| {pc['mean_abs_diff']:.4f}")
    print(f"  Pearson r(R1, R20) = {pc['pearson_r1_vs_r20']:.3f}  -> {pc['verdict']}")

    result = ss.analyse("study4")
    result["precision_check"] = pc
    result["rq11_decoupled"] = rq11(runs)
    result["protocol"] = payload["protocol"]
    result["pre_registered_commit"] = payload["pre_registered_commit"]

    print("\n=== RQ10: concordance by estimator (frozen Study 2 outcome) ===")
    print(f"{'estimator':<16}{'pooled':>20}{'within family':>22}{'within dataset':>22}{'strictest':>22}")
    for e in ESTIMATORS:
        s = result["diagnostics"][e]["stratifications"]
        def cell(k):
            d = s[k]
            if d["concordance"] is None:
                return f"{'NA':>22}"
            return f"{d['concordance']:>10.3f} [{d['ci_low']:.2f},{d['ci_high']:.2f}]".rjust(22)
        print(f"{e:<16}{cell('pooled')[-20:]:>20}{cell('within_family')}{cell('within_dataset')}"
              f"{cell('within_dataset_family_rate')}")

    print("\n=== P13 control: between-dataset Spearman rho ===")
    for e in ESTIMATORS:
        rho = result["diagnostics"][e]["between_dataset_ordering"]["spearman_rho"]
        print(f"  {e:<16} rho = {rho:+.3f}" if rho is not None else f"  {e:<16} rho = NA")

    print("\n=== within-dataset concordance by corruption family ===")
    fams = result["families"]
    print(f"{'estimator':<16}" + "".join(f"{f:>18}" for f in fams))
    for e in ESTIMATORS:
        pf = result["diagnostics"][e]["per_family"]
        cells = []
        for f in fams:
            v = pf[f]["within_dataset"]["concordance"]
            cells.append(f"{'NA':>18}" if v is None else f"{v:>18.3f}")
        print(f"{e:<16}" + "".join(cells))

    r11 = result["rq11_decoupled"]
    print(f"\n=== RQ11 (EXPLORATORY): decoupled sigma_even vs G_decoupled ===")
    print(f"  recomputed poor: {r11['n_poor']}/{r11['n_runs']}")
    for k in ("pooled", "within_family", "within_dataset"):
        d = r11["stratifications"][k]
        if d["concordance"] is None:
            print(f"  {k:<16} NA")
        else:
            print(f"  {k:<16} {d['concordance']:.3f} [{d['ci_low']:.2f}, {d['ci_high']:.2f}]")

    out = RESULTS / "study4_estimator_scores.json"
    with open(out, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
