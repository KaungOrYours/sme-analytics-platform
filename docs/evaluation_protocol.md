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

## 2. Prerequisite: the warnings being evaluated don't exist in code yet

Checked 2026-10-16: `backend/services/automl.py` and `cleaner.py` have no reliability-warning signals today.
What exists: `calculate_quality_score` (cleaner.py, completeness/uniqueness/type-consistency mean) and a
`confidence` field used only for problem-type detection (cleaner.py:316-382) — neither is a warning about
model-selection reliability.

Before the Week 4 warnings evaluation can run, three signals need to be added to `automl.py`, each cheap
because the groundwork is already there:

| Warning | Signal | Why it's cheap |
|---|---|---|
| Low rows-to-features ratio | `n_rows / n_features_after_encoding` below a threshold | One line from `X_train.shape` |
| Unstable cross-validation | std of `cross_val_score` across folds, already computed per candidate model at automl.py:313 (classification) / :457 (regression), currently discarded | Just needs to be kept and returned instead of thrown away |
| Suspected leakage | CV score (or train-vs-CV gap) implausibly high, e.g. CV accuracy/R² above a fixed ceiling | Heuristic on a number already computed |

This is tracked as a separate, scoped code task before Week 4 (not a redesign) — see
`.claude/skills/SMEAnalysis/MEMORY.md` Change Log for when it lands.

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

- Exact dataset list (OpenML-CC18 + UCI picks) and the full-protocol-vs-lighter-pass split — Section 4
  task for this week, goes in `docs/datasets.md`.
- Tuning-budget specifics for the manual baseline — goes in `evaluation/README.md` when the harness is
  scaffolded.
