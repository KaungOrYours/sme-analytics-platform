# Evaluation harness

Research harness for this project's evaluation studies. Deliberately separate from the application
(`backend/`, `frontend/`): this code evaluates the pipeline, it is not part of it. It imports the
application's own `build_preprocessor` rather than reimplementing preprocessing, so what is measured
is the real pipeline.

**Start with [`../docs/findings.md`](../docs/findings.md)** for what the studies concluded. Each
study record carries a banner stating what in it has been superseded.

## Current, results-producing code

| File | Purpose |
|---|---|
| `diagnostics.py` | Core measurement: one pipeline run, automated and manual, returning n, p, cross-validation scores, `sigma_CV`, signed `G = S_CV - S_test`, and the raw test labels and probabilities so intervals can be recomputed without rerunning a model. |
| `diagnostics2.py` | Study 2's four added diagnostics (`EPV`, `fold_contamination`, `evalml_cov`, `evalml_range`) and the two-sided failure labels. |
| `injectors.py` | Four seeded error injectors, each returning the corrupted frame plus exact ground truth. Shared by old and current code; not superseded. |
| `full_run.py` | Study 1 Experiment 1 (missing values). `python -m evaluation.full_run {development\|final-evaluation}` |
| `full_run_extended.py` | Study 1 Experiments 2-3 (duplicates, outliers). |
| `full_run_sample_size.py` | Study 1 Experiment 4 (training-partition halving). |
| `full_run_study2.py` | Study 2. Group C requires an explicit `--confirm` flag so the confirmation holdout cannot be opened by reflex. |
| `full_run_study3_transfer.py` | Study 3's external transfer sample (8 datasets, 500 < n <= 1000). |
| `recalibrate_study3.py` | Study 3's leave-one-dataset-out threshold recalibration. |
| `score_rq2.py` | Study 1 scoring: confusion matrices, MCC with the degenerate-case rule, run-level bootstrap. |
| `score_rq3_combination.py` | The OR/AND combination rule, fitted on development and locked before being applied to final-evaluation. |
| `score_study2.py` | Study 2 scoring, reusing `score_rq2.py`'s primitives unchanged so figures stay comparable. |
| `score_stratified.py` | **Post-hoc stratified re-analysis (not pre-registered).** Between- versus within-dataset discrimination, dataset-clustered bootstrap, estimable-cluster accounting. Also recomputes the previously ad-hoc AUROC tables so they are auditable. |
| `pilot.py` | The approved plan's required pilot, run before the Study 1 protocol was frozen. |
| `full_run_study4.py` | Study 4, which re-measures Study 2's same 525 runs with cross-validation repeated at R=10 and R=20. Protocol was committed before this file existed. |
| `score_study4.py` | Study 4 scoring. |
| `score_delta_sensitivity.py` | **Post-hoc (not pre-registered).** Recomputes the outcome label across a five-point `delta_G` grid and rescales the thresholded and stratified figures at each point. |
| `score_diagnostic_differences.py` | **Post-hoc (not pre-registered).** Paired dataset-clustered bootstrap over diagnostic pairs, so shared noise cancels instead of comparing two separately-computed intervals. |
| `score_algebraic_floor.py` | **Post-hoc (not pre-registered).** The permutation floor under within-dataset concordance, the cross-validation-mean confound behind the sub-chance reading, and the corruption-family and `delta_G` sensitivities of the between-dataset correlation. |
| `score_clustered_intervals.py` | **Post-hoc (not pre-registered).** Every headline interval re-derived at the dataset unit, plus paired intervals on the recalibration gains. Reproduces the six published anchor MCCs exactly as its validation gate. |
| `score_outcome_reliability.py` | **Post-hoc (not pre-registered).** How reliably the outcome is measured at run resolution: ICC, kappa, Hanley-McNeil standard errors, and a leave-one-seed-out oracle ceiling. |
| `score_partition_null.py` | **Post-hoc (not pre-registered).** Whether a frozen threshold's across-group spread is distinguishable from randomly re-partitioning the same datasets, by permutation. |
| `predictions_table.py` | The P1-P14 pre-registered predictions and their dispositions, each re-derived from the stored run records rather than carried over from the study write-ups. |
| `build_appendix_tables.py` | Generates the manuscript's dataset manifest, protocol-freeze evidence, diagnostic grid and positives-concentration tables as LaTeX, so no figure in them is hand-typed. Output directory is set with `--out`. |
| `make_threshold_figure.py` | Renders the leave-one-dataset-out threshold-refit spread as a figure, normalised by each rule's own published anchor. Output directory is set with `--out`. |
| `export_public_results.py` | Builds `results_public/`: the aggregate score files unchanged, and the per-run records with every row-level array replaced by counts, because the raw records embed the original class label of every test row and several datasets' licences do not permit redistributing that. |
| `study2_dataset_split.json` | The deterministic Study 2 group assignment. |
| `backend_path.py` | Puts `backend/` on `sys.path` so this code imports `services.*` the same way `backend/main.py` does, without making `backend/` a package. |

Results are written to `results/` as JSON, one record per run. `results/` and `data/` are not
committed: results are regenerable and datasets are fetched on demand.

## Superseded code, retained deliberately

`cleaning_eval.py`, `comparison_runner.py`, `warnings_eval.py`, `datasets.py` and
`run_experiment.py` were built for an earlier, pre-approval research design. Each says so in its own
docstring. They are kept as working reference code rather than deleted, so that a reader of the code
appendix encountering them is not left guessing why they disagree with the current protocol. **They
are not a source of current results.**

<details>
<summary>Original 2026-10-19 and 2026-10-20 status notes (superseded, kept for history)</summary>

2026-10-19: harness built and smoke-tested, full protocol run not yet done; needed the dataset
shortlist locked first.

2026-10-20: the full protocol run has happened; the pre-approval files listed above became
superseded at that point.

</details>

## Legacy file reference

### Pre-approval harness, file by file

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
  module's docstring, not `pytest`.
