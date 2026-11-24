"""Export a redistributable copy of the evaluation results.

Why this exists
---------------
Every figure in the write-up comes from `evaluation/results/`, and none of it is
checkable by a reader because that directory is not versioned. That is a real
problem: a silent key mismatch in one scoring module once produced a `null` that
was read as a finding and reached a draft abstract. Nobody working from a PDF
could have caught it.

The obvious fix -- commit `evaluation/results/` -- is not available, because the
run records embed the original target label of every test row: 96,684 labels
across 14 files. The 33 source datasets do not uniformly permit that. PMLB ships
no licence metadata at all; 14 of the 33 have no licence statement findable at
any primary source; and one, `irish`, carries an explicit restriction naming its
copyright holders, limiting use to statistical-methods research, and granting
redistribution to a single named archive rather than to downstream redistributors.

So this module exports what can be redistributed and omits what cannot:

  - All `*_scores*.json` are copied unchanged. They are aggregates -- concordances,
    correlations, confusion-matrix totals, bootstrap intervals -- and contain no
    row-level data from any source dataset.

  - In `*_results.json`, every per-row array is REMOVED and replaced by the
    summary statistics the analyses actually consume. `y_test` becomes
    `n_test_pos` / `n_test_neg` / `n_test`, which is all `score_outcome_reliability`
    ever derived from it; `test_proba` is dropped, as no committed scoring module
    reads it. Every diagnostic, every score and every label is retained, so each
    scoring module reproduces its published output from the export.

Stripping is applied uniformly rather than per dataset. Deciding case by case
would mean asserting a redistribution right for 19 datasets on the strength of an
absent licence statement, and absence of a statement is not a grant.

What a reader does with it
--------------------------
    cp -r evaluation/results_public evaluation/results
    backend/venv/bin/python3 -m evaluation.score_clustered_intervals

The run records remain sufficient to re-score. They are NOT sufficient to re-run
the pipeline: for that, fetch the datasets from PMLB. Note that `pmlb` resolves
against a mutable upstream branch with no commit pin, so a re-run is not
guaranteed to see the same bytes we did.

Run from the REPO ROOT:
    backend/venv/bin/python3 -m evaluation.export_public_results
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent / "results"
PUBLIC_DIR = Path(__file__).resolve().parent / "results_public"

# Per-row arrays carrying source-dataset content. Removed from every export.
ROW_LEVEL_KEYS = ("y_test", "test_proba", "y_train", "train_proba")


def summarise_rows(block):
    """Replace a block's per-row arrays with the counts the analyses consume."""
    if not isinstance(block, dict):
        return block, 0
    stripped = 0
    y = block.get("y_test")
    if isinstance(y, list) and y:
        codes = sorted(set(y))
        if len(codes) == 2:
            block["n_test_pos"] = sum(1 for v in y if v == codes[-1])
            block["n_test_neg"] = sum(1 for v in y if v == codes[0])
        block["n_test"] = len(y)
        # Codes are retained because three datasets use non-standard encodings
        # ({1,2} and {0,2}) and a reader re-deriving class balance from the
        # export would otherwise get it wrong.
        block["test_label_codes"] = codes
    for key in ROW_LEVEL_KEYS:
        if key in block:
            value = block.pop(key)
            stripped += len(value) if isinstance(value, list) else 1
    return block, stripped


def strip_record(record):
    """Recurse to arbitrary depth rather than assuming where the arms sit.

    Most run records carry `automated`/`manual` at the top level, but the
    sample-size files nest them one deeper under `full_size`/`half_size`. A
    shape-specific stripper silently missed those and left 168 row-level arrays
    in an export that claimed to have none, so this walks the whole structure.
    """
    total = 0
    if isinstance(record, list):
        for i, item in enumerate(record):
            record[i], n = strip_record(item)
            total += n
        return record, total
    if not isinstance(record, dict):
        return record, 0

    if any(k in record for k in ROW_LEVEL_KEYS):
        record, n = summarise_rows(record)
        total += n
    for key, value in list(record.items()):
        if isinstance(value, (dict, list)):
            record[key], n = strip_record(value)
            total += n
    return record, total


def export():
    if not RESULTS_DIR.exists():
        raise SystemExit(f"{RESULTS_DIR} not found; nothing to export.")
    if PUBLIC_DIR.exists():
        shutil.rmtree(PUBLIC_DIR)
    PUBLIC_DIR.mkdir(parents=True)

    copied, rewritten, stripped_total = [], [], 0

    for path in sorted(RESULTS_DIR.glob("*.json")):
        with path.open() as fh:
            try:
                payload = json.load(fh)
            except json.JSONDecodeError:
                print(f"  SKIP (unparseable): {path.name}")
                continue

        if "_results" not in path.name:
            shutil.copy2(path, PUBLIC_DIR / path.name)
            copied.append(path.name)
            continue

        runs = payload.get("runs") if isinstance(payload, dict) else payload
        count = 0
        if isinstance(runs, list):
            for i, record in enumerate(runs):
                runs[i], n = strip_record(record)
                count += n
        # A few result files are a bare list of runs rather than a dict; wrap
        # them so the note has somewhere to live without changing the records.
        if not isinstance(payload, dict):
            payload = {"runs": runs}
        payload["_redistribution_note"] = (
            "Per-row arrays removed. The source datasets do not uniformly permit "
            "redistribution of row-level content, and one carries an explicit "
            "restriction. Summary counts retained; all diagnostics, scores and "
            "labels are intact, so every scoring module reproduces its published "
            "output from this file."
        )
        with (PUBLIC_DIR / path.name).open("w") as fh:
            json.dump(payload, fh, indent=1)
        rewritten.append((path.name, count))
        stripped_total += count

    return copied, rewritten, stripped_total


def main():
    copied, rewritten, stripped = export()
    print()
    print("REDISTRIBUTABLE EXPORT")
    print(f"  destination        {PUBLIC_DIR}")
    print(f"  copied unchanged   {len(copied)} aggregate score files")
    print(f"  rewritten          {len(rewritten)} run-record files")
    print(f"  row values removed {stripped}")
    print()
    for name, count in rewritten:
        print(f"    {name:<46} {count:>6} removed")
    print()
    size = sum(f.stat().st_size for f in PUBLIC_DIR.glob("*.json"))
    print(f"  export size        {size / 1e6:.1f} MB")
    print()
    print("  A reader re-scores with:")
    print("    cp -r evaluation/results_public evaluation/results")
    print("    backend/venv/bin/python3 -m evaluation.score_clustered_intervals")
    print()


if __name__ == "__main__":
    main()
