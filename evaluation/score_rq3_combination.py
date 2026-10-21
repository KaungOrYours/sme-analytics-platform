"""
RQ3's "combination rule", the part of the frozen protocol not yet scored.

docs/evaluation_protocol.md Section 1, RQ3 (verbatim): "Do the diagnostics
PLUS A COMBINATION RULE, fit on the development group, show similar
discrimination on the disjoint final-evaluation group?" score_rq2.py only
ever scored n/p and sigma_cv individually -- this script builds and scores
the combination rule that sentence actually asks for, closing a gap in the
already-committed design rather than adding new scope.

Combination rule candidates: logical OR (triggered if either diagnostic
fires) and logical AND (triggered only if both fire). No trained
classifier/meta-learner is used to combine them -- picking a threshold-free
learned combiner would blur the exact distinction docs/literature_matrix.md
draws against Lahoti, Gummadi & Weikum (2023)'s Risk Advisor, which this
project deliberately avoids (a trained secondary model). OR/AND are the
only combinations possible without training something new.

Procedure, mirroring the project's existing anti-optimistic-bias pattern
(decide on development, test transfer on final-evaluation, never the
reverse): score OR and AND on the DEVELOPMENT group only, pick whichever
has the higher MCC there (ties broken toward OR, the more conservative/
higher-recall choice for a "distrust this" warning), freeze that choice,
then apply the SAME locked rule to the FINAL-EVALUATION group and report
its discrimination there. The development-group comparison is diagnostic
only -- RQ3's actual question is the final-evaluation number.

Usage: python -m evaluation.score_rq3_combination development
       python -m evaluation.score_rq3_combination final_evaluation
   (run development first to see which rule gets locked)
"""
import json
import sys
from pathlib import Path

from evaluation.score_rq2 import (
    DELTA_G, N_BOOTSTRAP, bootstrap_aggregate_metrics, confusion, mcc,
    np_triggered, poor_label, precision_recall_far, resolve_results_path,
    sigma_cv_triggered,
)

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def or_triggered(run):
    return 1 if (np_triggered(run) == 1 or sigma_cv_triggered(run) == 1) else 0


def and_triggered(run):
    return 1 if (np_triggered(run) == 1 and sigma_cv_triggered(run) == 1) else 0


def score_rule(name, triggered, poor):
    tp, fp, fn, tn = confusion(triggered, poor)
    precision, recall, far = precision_recall_far(tp, fp, fn, tn)
    m = mcc(tp, fp, fn, tn)
    degenerate = any(s == 0 for s in [(tp + fp), (tp + fn), (tn + fp), (tn + fn)])
    agg_ci = bootstrap_aggregate_metrics(triggered, poor)
    print(f"\n{name}:")
    print(f"  confusion (triggered x poor): TP={tp} FP={fp} FN={fn} TN={tn}")
    print(f"  precision={precision if precision is None else round(precision,3)} "
          f"recall={recall if recall is None else round(recall,3)} "
          f"false_alarm_rate={far if far is None else round(far,3)} "
          f"MCC={round(m,3)}{'  (degenerate -> MCC forced 0)' if degenerate else ''}")
    mcc_ci = agg_ci.get("mcc")
    if mcc_ci:
        print(f"  MCC 95% bootstrap CI: [{mcc_ci['ci_lower']:.3f}, {mcc_ci['ci_upper']:.3f}]")
    return {
        "name": name, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": precision, "recall": recall, "false_alarm_rate": far,
        "mcc": m, "degenerate": degenerate, "aggregate_bootstrap_ci": agg_ci,
    }


LOCK_FILE = RESULTS_DIR / "rq3_combination_rule_locked.json"


def main():
    if len(sys.argv) != 2:
        print("Usage: python -m evaluation.score_rq3_combination {development|final_evaluation}")
        sys.exit(1)
    group = sys.argv[1]
    results_path = resolve_results_path(group)
    if not results_path.exists():
        print(f"No results file at {results_path}")
        sys.exit(1)
    results = json.loads(results_path.read_text())
    poor = [poor_label(r) for r in results]
    print(f"Group: {group} ({len(results)} automated-pipeline runs, {sum(poor)} poor)")

    or_scored = score_rule("OR (n/p<10 OR sigma_cv>0.10)", [or_triggered(r) for r in results], poor)
    and_scored = score_rule("AND (n/p<10 AND sigma_cv>0.10)", [and_triggered(r) for r in results], poor)

    if group == "development":
        # Decide and freeze which rule transfers to final-evaluation, based
        # ONLY on development-group performance -- ties toward OR (higher
        # recall is the more conservative choice for a "distrust this"
        # warning).
        locked_rule = "AND" if and_scored["mcc"] > or_scored["mcc"] else "OR"
        LOCK_FILE.write_text(json.dumps({
            "locked_rule": locked_rule,
            "development_or_mcc": or_scored["mcc"], "development_and_mcc": and_scored["mcc"],
            "reason": "higher MCC on development group (ties toward OR)",
        }, indent=2))
        print(f"\nLOCKED combination rule for final-evaluation transfer: {locked_rule} "
              f"(dev MCC: OR={round(or_scored['mcc'],3)}, AND={round(and_scored['mcc'],3)})")
        print(f"Wrote lock file to {LOCK_FILE}")
    else:
        if not LOCK_FILE.exists():
            print("\nNo locked rule found -- run 'python -m evaluation.score_rq3_combination development' first.")
            sys.exit(1)
        lock = json.loads(LOCK_FILE.read_text())
        locked = lock["locked_rule"]
        locked_scored = or_scored if locked == "OR" else and_scored
        print(f"\nRQ3 answer -- locked rule is {locked} (chosen on development group, MCC={round(lock['development_or_mcc'] if locked=='OR' else lock['development_and_mcc'],3)}):")
        print(f"On final-evaluation (disjoint group): MCC={round(locked_scored['mcc'],3)}, "
              f"precision={locked_scored['precision']}, recall={locked_scored['recall']}")

        out = {
            "group": group, "locked_rule": locked, "locked_rule_dev_mcc": lock,
            "or_scored": or_scored, "and_scored": and_scored,
        }
        out_path = RESULTS_DIR / f"{group}_rq3_combination_scores.json"
        out_path.write_text(json.dumps(out, indent=2, default=str))
        print(f"Wrote RQ3 combination scoring to {out_path}")


if __name__ == "__main__":
    main()
