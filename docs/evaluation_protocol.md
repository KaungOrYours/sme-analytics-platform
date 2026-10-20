# Evaluation Protocol — FROZEN 2026-10-19

Supersedes the earlier draft entirely. Rewritten to match the approved PDM plan
(`Project and Data Management Plan (Kaung Htet).pdf`, submitted and approved by Dr. Rama, 14 Oct 2026),
after running the required pilot (`evaluation/pilot.py`, results in `evaluation/results/pilot_results.json`
— not committed, regenerate by rerunning the script). Per Cawley & Talbot (2010), every numeric choice below
was fixed from the pilot and literature alone, before any full-protocol outcome was observed. If a later run
makes any of these look wrong (e.g. almost everything or nothing gets labelled "poor"), that is a finding to
report, not a reason to go back and adjust the numbers.

## 1. Research questions (locked, verbatim from the approved plan)

**RQ1 (contextual benchmark)**: What is the difference in the automated pipeline's performance, compared to
the manual baseline, in small-data and training-corruption scenarios? Both pipelines run on the same outer
partitions, the same pre-declared metrics, and a fixed wall-clock budget B per dataset; manual-baseline
preprocessing and model family are fully prespecified in advance.

**RQ2 (primary contribution)**: Do runs with excessive validation-to-test optimism differ in sigma_CV (std
of cross-validation scores), and does sigma_CV provide additional discriminative information over n/p alone?
`G = S_CV,selected - S_test`; `poor = 1[G > delta_G]`; delta_G is fixed in advance, independent of n/p and
sigma_CV. Each diagnostic is scored independently; a combined signal is not assumed superior to either alone.

**RQ3 (preliminary transfer)**: Do the diagnostics plus a combination rule, fit on the development group,
show similar discrimination on the disjoint final-evaluation group? Explicitly a preliminary assessment, not
a confirmatory generalisation test (only 7 datasets total).

## 2. Diagnostics measured (exactly 2 — no leakage warning)

Per `docs/literature_matrix.md`: no valid, deployable leakage detector was found in the literature review, so
per the approved plan's own rule, **no leakage-flag diagnostic is included in this formal evaluation.** The
`suspected_leakage` warning in `backend/services/automl.py` remains in the live app (a UX feature, defensible
on its own terms) but is explicitly out of scope for RQ1-RQ3.

| Diagnostic | Definition | Computed by |
|---|---|---|
| n/p | outer-training rows / post-encoding feature count, both frozen before outcome observation | `evaluation/diagnostics.py: run_automated/run_manual_baseline` (`n`, `p`) |
| sigma_CV | std (ddof=1) of the selected model's per-fold CV AUROC scores | `evaluation/diagnostics.py: cv_scores_for_model` |

## 3. Metric

**AUROC** for both S_CV (mean across folds for the selected/only model) and S_test — threshold-free, robust
to the class imbalance present in several selected datasets (e.g. `appendicitis`, 85/21). Frozen choice, not
revisited per dataset.

## 4. "Poor" outcome — frozen definition

```
G = S_CV,selected - S_test
poor = 1 if G > delta_G else 0
delta_G = 0.05  (AUROC points)
```

Signed, not absolute — this measures *optimism* (validation looked better than test), the specific construct
RQ2 is about, not instability in either direction (a model that validates *worse* than it tests is not what
"validation-to-test optimism" means, even though it would trip an absolute-gap rule).

**delta_G = 0.05 is a round number fixed before seeing the full-protocol results**, chosen only from the
pilot's observation that it labels a non-trivial minority (~11% of 27 pilot runs) as poor — neither near-zero
(no signal to study) nor near-100% (no contrast to study). It is not derived from n/p or sigma_CV, per the
approved plan's independence requirement. State this number as a stated design choice in the report, and be
ready to justify 0.05 specifically in the viva (same treatment as every other fixed threshold in this
project — see `CLAUDE.md` Section 5's note on `calculate_quality_score`).

## 5. Diagnostic thresholds (for precision/recall/false-alarm/MCC scoring)

RQ2 needs each diagnostic binarised ("triggered" / not) to score precision, recall, false-alarm rate, and
MCC against the poor/not-poor label. Both thresholds below are anchored to an external source, not fit to
this project's own pilot data, to avoid the same optimistic-bias risk delta_G is designed to avoid:

- **n/p < 10** — the classic "events per variable" heuristic for logistic-regression reliability (Peduzzi et
  al., 1996; a long-standing biostatistics rule of thumb, cited here as an external anchor, not invented for
  this project). Flag any run below this.
- **sigma_CV > 0.10** — adapted from EvalML's own `AutoMLSearch._check_for_high_variance` (Alteryx, n.d.;
  the literal real-world precedent RQ2 is testing the validity of), which flags high CV variance when the
  score *range* (max-min across folds) exceeds 50% of the metric's full possible range. Range and standard
  deviation measure related but different things, and the approved plan specifies sigma_CV, so this is an
  adapted analogue, not a direct reuse of EvalML's number — stated explicitly as an adaptation, not claimed
  as identical to EvalML's rule. 0.10 is 10% of the full 0-1 AUROC range, fixed as a round number before
  seeing full-protocol results.

Both are genuine external anchors, but both required a judgement call to adapt to this project's exact
setup — flag this honestly in the report's methodology chapter and be ready to defend the adaptation
reasoning in the viva, not just the literature citation.

## 6. MCC edge-case rule

If any marginal sum of the 2x2 confusion matrix (triggered x poor) is zero — e.g. a diagnostic never
triggers, or every run is poor — the MCC denominator is zero and MCC is undefined by the raw formula.
**Frozen rule**: MCC = 0 in this case, matching scikit-learn's `matthews_corrcoef` convention and the
recommendation in Chicco & Jurman (2020) for degenerate confusion matrices. Report when this rule fires —
it is itself informative (e.g. a diagnostic that never triggers across the whole development group is a
finding, not a scoring artifact to hide).

## 7. Corruption design

- **One corruption family: missing values (MCAR)** — simplest, most standard, avoids extra assumptions
  about *why* data is missing; also the error type most directly tied to n (missingness reduces usable rows
  if list-wise deletion were used, though this pipeline imputes rather than drops, per `cleaner.py`).
- **Two non-zero levels, plus clean**: 0% (clean), 15%, 35% — the exact two non-zero rates piloted; chosen
  to be moderate and severe without re-running the pilot at other rates, consistent with freezing from
  pilot evidence rather than open-ended tuning.
- **Corruption applies only to the outer-training partition.** The held-out test partition is never
  corrupted, at any level, for any run — enforced in code by splitting outer train/test *before* calling
  the injector (`evaluation/pilot.py: run_one`, same pattern to be reused for the full run).
- **One sample-size level**: each dataset's full natural size (no subsampling). "Sample size" is not varied
  as an experimental factor in this design — each dataset contributes its own frozen n.
- **Three seeds**: 1, 2, 3. Controls the outer train/test split and all model/CV randomness.
- Conditional, not committed: a second corruption family or sample-size level may be added only if time and
  the development-group results allow — capped so the worst-case workload stays near 90-120 jobs, not the
  360-480 an unconstrained design would need. Not started; revisit after the development-group run.

## 8. Wall-clock budget B

**B = 30 seconds per dataset per pipeline.** Generous, not a binding constraint at this scale — the pilot's
actual runtime was ~0.2-0.3s per run (27 runs, 6.4s total), so B exists to satisfy the approved plan's
"fixed wall clock budget" requirement and to catch a genuine runaway run, not because compute is scarce here.

## 9. Bootstrap CI procedure

Per-run uncertainty on S_test (not on G, and not on aggregate warning precision/recall — kept conceptually
separate, per the approved plan):

- 1000 resamples.
- **Paired**: each resample draws (label, prediction) pairs together, preserving the label-prediction
  correspondence — never resample labels and predictions independently.
- **Stratified by class**: resample within each class separately (preserving the original test-set class
  proportions) and recombine, rather than a single unstratified draw — this is what the approved plan's
  "stratified sampling if a resample calls for drawing a single class" requires, and stratifying always
  (not just conditionally) is the simplest way to guarantee it never happens, for any test-set size.
- Report the 95% interval (2.5th/97.5th percentile of the 1000 resampled AUROC values) alongside the raw
  S_test and the thresholded "poor" label.
- **Explicitly an interval on test-set sampling uncertainty only** — it does not account for variance from
  the training-sample draw, fold composition, or the AutoML model-selection process, all of which also
  contribute to how much a single G value should be trusted. State this caveat every time the interval is
  reported, not just once in the methods section.

Aggregate precision/recall/MCC uncertainty (across the whole development or final-evaluation group) is a
separate quantity from the per-run S_test interval above. **Decided and implemented 2026-10-20**
(`evaluation/score_rq2.py: bootstrap_aggregate_metrics`): non-parametric bootstrap over the RUN as the
resampling unit — resample n runs with replacement (n = group size), recompute the confusion matrix and all
four metrics each time, report the 2.5th/97.5th percentile across 1000 resamples. **Stated limitation**: runs
within a group are not fully independent (each dataset contributes 9 correlated runs via 3 rates x 3 seeds),
so this treats correlated runs as exchangeable. A cluster bootstrap over datasets would respect that
structure better but with only 3-4 clusters per group would be far noisier, not more rigorous — the run-level
bootstrap was chosen as the more informative of the two imperfect options, not because it is assumption-free.

## 10. Datasets

See `docs/datasets.md` for the full manifest (7 PMLBmini/TabMini datasets, 4 development + 3
final-evaluation, selected to span n/p from 1.86 to 100).

## 11. Pipelines

- **Automated**: selects among {Random Forest, Logistic Regression, Decision Tree} by mean CV AUROC, no
  hyperparameter search (same no-tuning philosophy as the live app's `automl.py`). Implemented in
  `evaluation/diagnostics.py: run_automated`.
- **Manual baseline**: a single, fully prespecified model — plain logistic regression, no model-selection
  step (there is only one candidate). Chosen because TabMini's own published finding is that a plain
  logistic regression is a strong, standard baseline other methods are measured against on exactly this
  kind of small tabular data — an externally-grounded choice, not an arbitrary pick. Implemented in
  `evaluation/diagnostics.py: run_manual_baseline`.
- Both share the same outer train/test split, the same preprocessing (`automl.py`'s `build_preprocessor`,
  fit on the training fold only), and the same CV scheme.

## 12. What's NOT yet run

This document freezes the design. It does not itself contain results. Next steps, in order:
1. Full run on the 4 development datasets across {clean, 15%, 35%} x 3 seeds = up to ~36-48 jobs
   (2 pipelines x 4 datasets x 3 rates x 3 seeds, before any conditional expansion) — answers RQ1 and scores
   the diagnostics for RQ2 on the development group.
2. Repeat on the 3 final-evaluation datasets — answers RQ3 (preliminary transfer).
3. Compute aggregate precision/recall/false-alarm/MCC for each diagnostic, with the bootstrap CI treatment
   from Section 9.
4. Only then consider the conditional second corruption family / sample-size level (Section 7), if time and
   results allow.

## Addendum (2026-10-20): RQ2 scope clarification + full-protocol run

The sections above freeze every *numeric* choice but do not say explicitly whether RQ2's diagnostic scoring
pools automated-pipeline and manual-baseline runs, or scores the automated pipeline only. Decided when
building the full-protocol runner (`evaluation/full_run.py`, `evaluation/score_rq2.py`): **automated-pipeline
runs only.** Reasoning: RQ2 and the dissertation's novelty claim are specifically about whether the automated
pipeline's own signals predict its own failures, not a pooled sample across both pipelines. The manual
baseline's G/sigma_CV are still recorded on every run (for RQ1's automated-vs-manual comparison) but are not
fed into the RQ2 precision/recall/MCC scoring. State this explicitly as an operationalisation decision in the
methodology chapter, not left implicit.

This also resolves an internal inconsistency in Section 12 above: "2 pipelines x 4 datasets x 3 rates x 3
seeds" is 72 total pipeline-runs, not the "~36-48 jobs" also stated there. 36 is exactly the automated-only
run count (4 x 3 x 3) that RQ2 scores; 72 is the total jobs both pipelines produce. The "36-48" range was
anticipating the conditional expansion in Section 7, which has not been exercised.

**Full-protocol run completed 2026-10-20 — this is Experiment 1** (not just the pilot): `evaluation/full_run.py`
for both groups, `evaluation/score_rq2.py` for RQ2/RQ3 scoring. Headline results in `docs/results_summary.md`.
Any later experiment (the Section 7 conditional expansion, a revisited aggregate-uncertainty method, etc.)
should be numbered Experiment 2 onward, both in this doc and in `docs/results_summary.md`, so the FPR's
results chapter has a stable numbering to cite.

**Section 7's conditional expansion exercised 2026-10-20 as Experiments 2-3** (duplicates, outliers), via a
new `evaluation/full_run_extended.py` that leaves `full_run.py`/Experiment 1 untouched. `inconsistent_
categories` was checked and excluded — all 7 datasets are 100% numerically encoded, so that injector would be
a no-op. Full results and three substantive findings (duplicates inducing genuine CV-fold leakage that `G`
correctly flags; outliers' pessimism-not-optimism signature falling outside the one-sided `poor` definition's
sensitivity; `n/p`'s apparent transfer success turning out to be missing-values-specific, not general) are in
`docs/results_summary.md`'s "Experiments 2-3" section — not duplicated here, since this document freezes
design, not results. One finding
surfaced during this run and documented in `docs/datasets.md`: the `irish` dataset's `Educational_level`
feature perfectly determines `target` (verified by crosstab, zero exceptions across 500 rows) — kept in the
dataset manifest unchanged per the student's explicit decision, and written up as a discussion-section case
study rather than engineered away, since it is a genuine illustration of the dissertation's own thesis.

## Design choices to defend in the viva (collected from the sections above)

- delta_G = 0.05 AUROC points (Section 4)
- n/p < 10 and sigma_CV > 0.10 thresholds, and why each is an *adaptation* of an external source rather than
  a direct reuse (Section 5)
- MCC = 0 edge-case convention (Section 6)
- Missing values as the one corruption family, and 15%/35% as the two levels (Section 7)
- Plain logistic regression as the manual baseline (Section 11)
