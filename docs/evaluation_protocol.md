# Evaluation Protocol

Written and locked 2026-10-16, before any evaluation experiment runs, per Dr. Rama's corrective action #2
(see `CLAUDE.md` Section 4). Any change to the research question, metrics, or the "poor performance"
definition below after experiments start must be noted in the Change Log of
`.claude/skills/SMEAnalysis/MEMORY.md` with a reason, since changing the target definition after seeing
results would undermine the evaluation.

## 1. Research question (locked)

How closely does an automated cleaning and model-selection pipeline match manually tuned models on small,
messy tabular datasets, and how well do its built-in reliability warnings predict when its results will be
poor?

Framing for the report and viva (per Rama, 2026-10-13): lead with the second half. The contribution is an
empirical framework for evaluating whether an automated pipeline's reliability warnings predict its own
failures. The pipeline and the manual-baseline comparison are the testbed that makes that question
answerable, not a parallel contribution.

## 2. The three warning signals (implemented 2026-10-19)

Checked 2026-10-16: at that point `backend/services/automl.py` and `cleaner.py` had no reliability-warning
signals. What existed was `calculate_quality_score` (cleaner.py, completeness/uniqueness/type-consistency
mean) and a `confidence` field used only for problem-type detection (cleaner.py:316-382) — neither is a
warning about model-selection reliability.

Implemented 2026-10-19 in `automl.py` (`build_reliability_warnings`, called from both `run_classification`
and `run_regression` after the best model is fit). Each warning is returned per-run in
`results["reliability_warnings"]` as `{name, triggered, value, threshold, message}`, so the evaluation
harness can consume it directly as a binary predictor:

| Warning | Signal | Threshold (design choice — justify in viva) |
|---|---|---|
| `low_rows_to_features_ratio` | `len(X_train) / n_features_after_encoding` | triggered if < 10 rows per feature |
| `unstable_cross_validation` | std of `cross_val_score` across folds for the *selected* model (previously computed then discarded at automl.py:313/:457, now kept) | triggered if std > 0.10 |
| `suspected_leakage` | the selected model's mean CV score | triggered if > 0.98 (same ceiling for accuracy and R², both 0-1-ish scales) |

These thresholds are not validated standards, same treatment as `calculate_quality_score` and the "poor
performance" definition in Section 4 below — state as a stated design choice in the report, not a given.
Unit-tested manually against synthetic data (low ratio: 2 categorical columns with 40-50 levels over 120
rows triggered correctly; leakage: a feature built from `target + tiny noise` triggered correctly; both
off on a clean random dataset). No automated test suite exists yet (see CLAUDE.md Section 5 "still open").

## 3. The three evaluation axes

Maps directly to Rama's per-component rigor table (`CLAUDE.md` Section 4).

1. **Cleaning-detection evaluation.** Inject missing values, duplicates, inconsistent categories, and
   outliers *separately* at 5/10/20%, on datasets with known ground truth. Measure: detection precision,
   detection recall, reconstruction accuracy vs. ground truth, and downstream effect on model performance.
2. **Model-selection benchmark.** Automated pipeline (fixed `n_estimators=50`, no hyperparameter search) vs.
   a manually tuned scikit-learn baseline (grid/random search). Same data splits, same metrics, same stated
   tuning budget, same information available to both — fixed here, before any run:
   - Splits: repeated stratified K-fold CV (classification) / K-fold (regression), fixed seeds, train/test
     held out once at the end exactly as the live pipeline already does.
   - Metrics: F1 (macro) and accuracy for classification; RMSE and R² for regression. Report mean and
     variance across seeds, not just mean.
   - Tuning budget for the manual baseline: stated explicitly in `evaluation/README.md` once the harness
     exists (e.g. a fixed grid, fixed number of random-search iterations) — written down before results are
     seen, so the comparison can't be tuned after the fact.
3. **Reliability-warnings evaluation (the novelty claim).** Each warning from Section 2, treated as a binary
   predictor of the "poor performance" outcome defined below. Scored by precision, recall, false-alarm rate,
   and discrimination (AUROC/AUPRC against the continuous held-out metric). Run across predefined
   sample-size levels, repeated at multiple fixed random seeds — not ad hoc subsampling.

## 4. Written definition of "poor performance" (locked)

A run (one dataset × one size level × one seed × one error condition) is labelled **poor** if either holds,
checked on the held-out test fold only:

- **Weak:** mean held-out metric is at or below a trivial baseline — majority-class F1/accuracy for
  classification, or R² ≤ 0 (worse than predicting the mean) for regression.
- **Unstable:** the gap between the cross-validated selection score (what the pipeline used to pick the
  model) and the held-out test score exceeds 0.10 absolute (classification metrics, 0-1 scale) or 0.15
  absolute (R²) — signalling the selection step overfit or got lucky.

Either condition alone is sufficient; a run can be weak without being unstable and vice versa. These
thresholds are a stated design choice, not a validated standard — flag this explicitly in the report's
methodology chapter (same treatment as `calculate_quality_score` in `CLAUDE.md` Section 5) and be ready to
justify the specific numbers in the viva.

This definition is what Section 3's warnings get scored against. It must not change after experiments
start; if it turns out to be wrong (e.g. everything gets labelled poor, or nothing does), that is itself a
finding to report, not a reason to quietly loosen the thresholds and rerun.

## 5. Not yet decided here (next steps)

- Exact dataset list (OpenML-CC18 + UCI picks) and the full-protocol-vs-lighter-pass split — a candidate
  shortlist is now drafted in `docs/datasets.md` (2026-10-19) but still needs the student's final
  confirmation and the licence/provenance checks before it's locked.
- The harness itself is now built (2026-10-19, ahead of the Week 2 schedule) — see `evaluation/README.md`
  for what exists and what's smoke-tested vs. what still needs the locked dataset shortlist to run for
  real. Tuning-budget for the manual baseline is already stated there (`comparison_runner.RF_PARAM_GRID`),
  not still pending.
- Still open: the exact sample-size levels and seed count for the full run (Section 3 point 3) aren't
  decided — needs stating explicitly, same treatment as everything else here, before the full run.
