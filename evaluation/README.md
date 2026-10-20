# Evaluation harness

Supports the locked research design in `docs/evaluation_protocol.md`. Separate from the app
(`backend/`, `frontend/`) per `CLAUDE.md` Section 7 — this code evaluates the pipeline, it isn't part of it.

**Status (2026-10-20, superseding the note below): the full protocol run has happened.** `cleaning_eval.py`,
`comparison_runner.py`, `warnings_eval.py`, `datasets.py`, and `run_experiment.py` below were built for an
earlier, pre-approval research design and are now superseded (each file says so in its own docstring) — kept
as working reference code, not as a source of current results. **The current, results-producing code is**
`evaluation/diagnostics.py` (core measurement), `evaluation/full_run.py` (Experiment 1: missing-values),
`evaluation/full_run_extended.py` (Experiments 2-3: duplicates, outliers), and `evaluation/score_rq2.py`
(RQ2/RQ3 scoring, including bootstrap CIs). Results are in `docs/results_summary.md`, not in this harness's
own output. `injectors.py` is shared by both the old and current code and is not superseded.

<details>
<summary>Original 2026-10-19 status note (superseded, kept for history)</summary>

**Status (2026-10-19): harness built and smoke-tested, full protocol run NOT yet done.** The full run
needs `docs/datasets.md`'s shortlist locked first (currently candidates only).

</details>

## What's here

| File | Purpose |
|---|---|
| `backend_path.py` | Adds `backend/` to `sys.path` so this code can import `services.automl`/`services.cleaner` the same way `backend/main.py` does, without turning `backend/` into a package. |
| `injectors.py` | Four error injectors (`inject_missing_values`, `inject_duplicates`, `inject_inconsistent_categories`, `inject_outliers`), each seeded, each returning the corrupted dataframe plus exact ground truth of what was changed. |
| `cleaning_eval.py` | Scores `backend/services/cleaner.py`'s `detect_problems`/`auto_clean` against that ground truth: detection precision/recall and reconstruction accuracy, per error type. |
| `comparison_runner.py` | RQ1: automated pipeline (`automl.run_automl`, fixed `n_estimators=50`) vs. a manually tuned baseline (`GridSearchCV` over the stated grid below) — same split, same preprocessing, same CV scheme. |
| `warnings_eval.py` | RQ2 (the novelty claim): the locked "poor performance" definition from `evaluation_protocol.md` Section 4, and precision/recall/false-alarm-rate/AUROC scoring of each reliability warning against it. |
| `datasets.py` | Dataset loaders. Currently one: Wholesale customers (UCI), used to build and prove the harness. |
| `run_experiment.py` | End-to-end **smoke test**, not the full protocol run — see below. |

## Reproducing the smoke test

```
cd backend && source venv/bin/activate && cd ..
python3 -m evaluation.run_experiment
```

Downloads the Wholesale customers dataset (cached in `evaluation/data/`, gitignored — re-fetched from
the UCI API on first run, not versioned), runs all 3 cleaning-detectable error types (missing, duplicate,
outliers — `inconsistent_categories` is skipped: this dataset has no categorical column) across
{5,10,20}% rates and 3 seeds, runs the automated-vs-manual comparison across the same 3 seeds, labels
each as poor/not-poor, and writes the full result set to `evaluation/results/smoke_test_<timestamp>.json`
(gitignored — a smoke-test artifact, not a results table for the report).

This proves the harness is wired correctly end-to-end. It is **not** a result to cite in the report — 3
seeds and 1 dataset aren't enough to score warning precision/recall meaningfully, and the dataset hasn't
been through the selection/ethics checks in `docs/datasets.md`.

## Known gaps before the full protocol run

- `inconsistent_categories` needs at least one dataset in the final shortlist with a categorical column —
  flagged in `docs/datasets.md`.
- The real seed count and the "predefined sample-size levels" referenced in `evaluation_protocol.md`
  Section 3 point 3 aren't decided yet — needs stating explicitly before the full run, same as the
  dataset shortlist.
- `comparison_runner.py`'s manual-baseline tuning grid (`RF_PARAM_GRID`: n_estimators in
  {50,100,200} x max_depth in {None,5,10,20}, 12 points) is a stated, fixed design choice for runtime
  reasons across many datasets — not an exhaustive search. State this as a scope limit in the report.
- No automated test suite — correctness so far is from the manual sanity checks described in each
  module's docstring and in `docs/ai_assistance_log.md`'s 2026-10-19 entries, not `pytest`.
