# Study 3 protocol — PRE-REGISTERED 2026-10-21, before any threshold was fitted

Extends `docs/study2_protocol.md`. Study 2's Claim 2 established that the diagnostics' weakness is
threshold calibration rather than construct, but deliberately stopped short of proposing recalibrated
thresholds, because fitting one requires an out-of-sample estimate. This document specifies how that
estimate is obtained, and is frozen before any threshold-fitting code was written or run.

## 1. The holdout problem, and why a new dataset sample is not the answer

Verified 2026-10-21 by enumerating all 162 PMLB classification datasets: **no dataset with a binary
target and n <= 500 exists outside the 44 raw PMLBmini candidates.** PMLBmini is exhaustive for that
criterion, which is how Knauer, Grimm and Rodner (2024) constructed it. Study 2 has now used all 25
of TabMini's ethically-curated survivors, so there is no fresh sample available inside the project's
own small-data regime. The 19 datasets TabMini excluded are not available either: several were
excluded for personally-identifiable-information and ethical-sensitivity reasons that this project's
own ethics criteria also bind it to respect, and cherry-picking the methodologically-excluded subset
while discarding the ethically-excluded one would make the curation argument incoherent.

The gap is therefore not a shortage of data but the need for an out-of-sample estimate of a *fitted*
quantity. Two independent routes are used, and both are specified here.

## 2. RQ8 and RQ9

**RQ8 (primary).** Can thresholds for the diagnostics be recalibrated so that their binary decisions
recover the discrimination their threshold-free scores demonstrably carry, and does a recalibrated
threshold generalise to datasets not used to fit it?

**RQ9 (external transfer).** Do thresholds fitted on the n <= 500 regime transfer to binary datasets
with larger n, outside the regime the project is scoped to?

## 3. Method for RQ8 — leave-one-dataset-out, fitted and evaluated disjointly

The resampling unit is the **dataset**, not the run, because runs within a dataset are correlated and
a threshold fitted on some of a dataset's runs would be evaluated on near-replicates of its own
fitting data.

For each of the 25 datasets d, and for each diagnostic X:
1. Fit a threshold `t*(X, d)` using **only the runs from the other 24 datasets**.
2. Apply `t*(X, d)` to dataset d's runs, which were not used in the fit, and record that confusion
   matrix.
3. Aggregate the 25 disjoint out-of-sample confusion matrices into one, and report precision, recall,
   false-alarm rate and MCC with the run-level bootstrap from `evaluation_protocol.md` Section 9,
   carrying its stated exchangeability limitation.

Every dataset is held out exactly once, so every reported figure is out-of-sample.

**Fitting criterion, fixed now: maximise MCC on the 24 fitting datasets' pooled runs.** MCC is the
criterion because it is the headline metric Study 1 and Study 2 both report and the one least
distorted by the minority poor label. Ties are broken toward the threshold closer to the diagnostic's
original frozen or vendor value, so that the procedure cannot drift away from the published anchor
without earning it.

**Threshold grid, fixed now:** 200 equally-spaced candidate values spanning the observed range of
that diagnostic across the fitting runs, inclusive of both endpoints. A grid rather than an optimiser
so the procedure is deterministic and reproducible without a seed.

**Thresholds are fitted pooled across corruption families, not per family.** This is a deliberate
realism constraint, not a convenience: a deployed diagnostic does not know which corruption is
present in the data it is given, so a per-family threshold is not a deployable artefact. Study 2's
mandatory within-family *reporting* is retained for the results.

**Diagnostics recalibrated:** all six, so that the comparison is uniform. `fold_contamination` is
included despite Study 2 refuting it, specifically so that recalibration cannot be claimed to rescue
a diagnostic whose continuous score anti-predicts the outcome. If recalibration appears to rescue it,
that is evidence the procedure is overfitting and must be reported as such.

**Comparison baseline:** each diagnostic's frozen or vendor threshold from Study 1 and Study 2,
evaluated on the same runs. The question is whether recalibration beats the published anchor
out-of-sample, not whether a fitted threshold beats a random one.

**Label:** `poor_optimism`, unchanged, `delta_G = 0.05`. Secondary labels are reported but no
threshold is fitted against them.

## 4. Method for RQ9 — external transfer beyond the regime

Eight binary PMLB datasets with 500 < n <= 1000, none of them in the 44 and none previously touched
by this project: `threeOf9` (n=512), `monk3` (554), `monk1` (556), `monk2` (601), `profb` (672),
`tic_tac_toe` (958), `tokyo1` (959), `xd6` (973).

**These are explicitly outside the project's n <= 500 small-data regime and are not added to it.**
They constitute a transfer test with a declared population difference, reported separately and never
pooled with the 25. Several are synthetic boolean-function benchmarks of the same family as `mux6`,
`corral` and `parity5`, so the `forces_duplication` stratification from Study 2 Section 5 applies and
is reported.

Procedure: run the same Study 2 grid (clean plus three corruption families at 15% and 35%, three
seeds), then apply **the thresholds fitted on the 25 small datasets, unchanged**, and report
out-of-sample performance. No threshold is refitted on these 8.

## 5. Pre-registered predictions

- **P7.** Recalibrated thresholds achieve materially higher out-of-sample MCC than the frozen or
  vendor thresholds for `evalml_range` and `EPV`, the two diagnostics Study 2 identified as
  specifically miscalibrated, and a smaller improvement for `sigma_cv`, whose frozen threshold of
  0.10 already sits in a reasonable region.
- **P8.** `fold_contamination` is **not** rescued by recalibration: its out-of-sample MCC remains at
  or below zero, consistent with its continuous score anti-predicting the outcome on Study 2's
  confirmation group.
- **P9.** Thresholds fitted on n <= 500 transfer to the 8 larger datasets with reduced but still
  positive out-of-sample MCC for the three cross-validation-variance diagnostics.
- **P10.** `n/p`'s out-of-sample MCC under leave-one-dataset-out is substantially lower than its
  +0.540 on Study 2's Group C, because that figure was a single favourable sample and Study 2
  Finding 3 showed the diagnostic swings between +0.540 and -0.004 across groups. This is a
  prediction that an apparently strong result will shrink when evaluated across all 25 held-out
  datasets rather than one group of 9.

## 6. What would falsify the Study 2 Claim 2 framing

If recalibrated thresholds do **not** beat the published anchors out-of-sample, then Study 2's Claim
2 ("the failure is calibration, not construct") is wrong, or at least not actionable: it would mean
the threshold-free signal cannot be converted into a usable binary decision rule by any single global
cut, which would point back toward the per-instance trained estimators (Lahoti, Gummadi and Weikum,
2023) that this project argues may be unnecessary. That outcome is reported as a refutation of Claim
2, not reframed.

## 7. Excluded

- No per-family thresholds (not deployable, see Section 3).
- No trained meta-learner, per Study 2 Section 10. A single scalar threshold per diagnostic, fitted
  by grid search on a disjoint dataset partition, is not a learned model of the instance.
- No refitting on the 8 transfer datasets.
- No new corruption family, metric, or `delta_G`.
