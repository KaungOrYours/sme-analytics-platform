# Study 4 results — the per-run null survives a 20x more precise estimator

**Protocol**: `docs/study4_protocol.md`, pre-registered and committed **alone** in `7cab9db`, before
`evaluation/full_run_study4.py` existed and before any Study 4 result existed. This is the first study
in the project whose git history proves its own freeze.

**Reactive motivation, repeated here as the protocol commits.** Study 4 exists because of a specific
objection to results the project had already published — that the absence of within-dataset
discrimination might be a property of the five-sample estimator rather than of the quantity it
estimates. The hypotheses were pre-registered, but the question was prompted by a known weakness
rather than posed before the data existed. That is weaker than Studies 2 and 3's position.

**525 runs, 0 skipped, 4,223 s.** 25 datasets, groups A+B+C pooled, automated pipeline only.
142 poor-labelled runs under Study 2's frozen `poor_optimism` label at `delta_G = 0.05`.
19 of 25 datasets are estimable (contain both outcome classes).

## 1. Validation gate: passed

`sigma_R1`, recomputed from scratch for the model Study 2 selected, reproduced Study 2's stored
`sigma_cv` **exactly for all 525 runs — 0 mismatches** (tolerance 1e-12). The reproduction of splits,
corruption, seeds and model selection is therefore exact, and the comparison below is valid. This
mirrors the reproduce-before-revise check that validated `evaluation/score_stratified.py`.

## 2. The estimators genuinely differ (protocol Section 9 check)

Section 9 named a specific way this study could have had no power: if 20 repeats produced
near-identical values to one split, nothing could be separated. That did not happen.

| | value |
|---|---|
| mean `sigma_R1` | 0.0863 |
| mean `sigma_R20` | 0.0885 |
| mean absolute per-run difference | **0.0256** |
| Pearson r(`sigma_R1`, `sigma_R20`) | **0.828** (no-power threshold was 0.95) |

The mean absolute disagreement is about 30 per cent of the mean value itself. The extra repeats
changed the number materially, and the within-dataset variance share of the diagnostic falls from
0.399 at R=1 to 0.238 at R=20 — the estimate did become substantially less noisy. **The study has
power to separate P11 from P12.**

## 3. RQ10: concordance by estimator, frozen outcome

Dataset-clustered bootstrap, 2,000 resamples, whole datasets resampled, seed 0.

| Estimator | Pooled | Within family | **Within dataset** | Within dataset x family x rate |
|---|---|---|---|---|
| `sigma_R1` (as shipped) | 0.660 [0.52, 0.77] | 0.735 [0.61, 0.84] | **0.332 [0.25, 0.41]** | 0.382 [0.26, 0.49] |
| `sigma_R10` | 0.677 [0.53, 0.78] | 0.772 [0.65, 0.86] | **0.301 [0.22, 0.39]** | 0.426 [0.32, 0.56] |
| `sigma_R20` | 0.679 [0.53, 0.79] | 0.774 [0.65, 0.87] | **0.265 [0.17, 0.37]** | 0.324 [0.23, 0.46] |
| `sigma_pooled20` | 0.683 [0.53, 0.79] | 0.775 [0.64, 0.87] | **0.251 [0.17, 0.35]** | 0.331 [0.21, 0.48]  |

Within-dataset concordance by corruption family:

| Estimator | clean | duplicates | missing_values | outliers |
|---|---|---|---|---|
| `sigma_R1` | 0.375 | 0.316 | 0.411 | 0.446 |
| `sigma_R10` | 0.417 | 0.306 | 0.421 | 0.500 |
| `sigma_R20` | 0.375 | 0.224 | 0.368 | 0.429 |
| `sigma_pooled20` | 0.333 | 0.224 | 0.347 | 0.357 |

**Within-dataset discrimination does not improve with estimator precision. It declines slightly.**
Every interval lies entirely below 0.5, and no corruption family shows a gain at R=20 over R=1.

## 4. Status of each pre-registered prediction

**P11 (estimator-artefact hypothesis): REFUTED.** P11 required within-dataset concordance to rise
monotonically with R and to clear 0.5 at R=20 in the `missing_values` and `duplicates` families. The
observed sequence is 0.332, 0.301, 0.265 — monotonically *decreasing* — and the two named families
move the wrong way too (`missing_values` 0.411 to 0.368; `duplicates` 0.316 to 0.224). The
imprecision of the shipped five-fold standard deviation does **not** explain the per-run null.

**P12 (estimand hypothesis): substantively CONFIRMED, and its second clause was badly worded.**
P12's first clause is satisfied exactly: within-dataset concordance stays inside Study 2's observed
0.139 to 0.435 band at every R. Its second clause as written — "the R=20 interval does not exclude
chance from below" — **is ambiguous and, read literally, is not satisfied**: the R=20 interval
[0.17, 0.37] lies wholly below 0.5. The intended meaning was that concordance would not rise to or
above chance, which is what happened. This is recorded as a defect in the pre-registration's wording
rather than resolved by choosing the reading that fits the data. **The substance of P12 — that the
per-run null is a property of the quantity and not of its estimate — is confirmed on the
unambiguous first clause and on the refutation of P11.**

**P13 (control): CONFIRMED.** Between-dataset Spearman rho is essentially flat across estimators:
+0.811, +0.790, +0.800, +0.790. The dataset-level signal does not depend on estimator precision,
exactly as predicted. Note these are computed over all 25 datasets with groups A, B and C pooled, and
are therefore **not** comparable with Study 2's +0.877 to +0.936, which were groups B and C scored
separately.

**P14 (RQ11, exploratory): REFUTED.** See Section 5.

## 5. RQ11: shared fold noise is not the explanation

`sigma_even` (mean per-repeat standard deviation over the 10 even-indexed repeats) and `G_decoupled`
(mean over the 10 **odd**-indexed repeats, minus `s_test`) share no fold scores at all. Under the
recomputed label, 131 of 525 runs are poor.

| Stratification | Concordance |
|---|---|
| Pooled | 0.653 [0.50, 0.77] |
| Within family | 0.755 [0.62, 0.85] |
| **Within dataset** | **0.265 [0.18, 0.36]** |
| Within dataset x family | 0.360 [0.25, 0.48] |
| Within dataset x family x rate | 0.369 [0.25, 0.51] |

Fully decoupled, the within-dataset figure is 0.265 — **indistinguishable from the coupled value and
still far below chance.** The mechanism Chapter 5 floated as a candidate for the sub-chance result,
and explicitly labelled untested, is refuted. It is not shared sampling noise.

## 6. Post-hoc: what does explain the sub-chance result

**This section is post-hoc and was not pre-registered.** It was prompted by Sections 3 to 5
eliminating both previously available explanations, and is reported as a mechanism with supporting
evidence, not as a tested prediction.

AUROC is bounded above by 1. Within a single dataset, a run whose cross-validation mean lands near
that ceiling is **forced** toward low fold-to-fold variance, while the same high mean raises
`G = S_CV - S_test` almost by construction. Low `sigma` would then accompany high optimism, which is
anti-prediction.

The data support this directly. Within-dataset Spearman correlations, median over the 25 datasets:

| Relationship | Median rho | Datasets with that sign |
|---|---|---|
| CV mean vs `sigma_R20` | **-0.830** | 24 of 25 negative |
| CV mean vs `G` | **+0.688** | 25 of 25 positive |
| `sigma_R20` vs `G`, raw | **-0.630** | 23 of 25 negative |
| `sigma_R20` vs `G`, **partialling out the CV mean** | **-0.084** | 14 of 24 negative |

**Corrected 2026-11-25.** This table was previously published with -0.813 in the first row, a
transcription error for -0.830, and with the partial correlation as -0.075 over "15 of 25" datasets.
Both are now computed by `evaluation/score_paper_figures.py::study4_partials` rather than by an
uncommitted script. The partial is **undefined for `irish`**, whose within-dataset rho between `G`
and the cross-validation mean is exactly 1.0, making the denominator zero; it is therefore reported
over the **24 datasets where it is defined**, not 25. Earlier figures of "15 of 25" and "14 of 25"
were both wrong on the denominator.

Controlling for the cross-validation mean collapses the anti-prediction from -0.630 to -0.084, which
is near zero and close to a coin flip on sign. **The sub-chance within-dataset concordance is
substantially a bounded-metric confound: the CV mean drives `sigma` down and `G` up at the same
time.** Twenty per cent of runs have a CV mean above 0.95, so the ceiling is not a rare corner of
this benchmark.

This also explains the mild *decline* with R in Section 3 as a coherent consequence rather than
noise: a more precise estimate of the fold standard deviation tracks the mean-induced component more
faithfully, so it tracks the confounder slightly better. That reading is plausible and is not
claimed as established.

## 7. What this changes

**Contribution 1 is strengthened and not corrected.** The per-run null survives a tenfold and
twentyfold increase in estimation precision, with the estimators demonstrably differing by about 30
per cent of their own magnitude. The claim moves from "no within-dataset signal was found" to "no
within-dataset signal is recoverable at this granularity by this class of estimator, and the residual
within-dataset association is a bounded-metric artefact." **This is not a fourth self-correction**:
the existing position stands, better defended.

**Contribution 2 is untouched.** It rests on threshold transfer and was already established three
independent ways.

**One open weakness is closed.** The sub-chance within-dataset figures were reported in Chapter 5 as
an open observation with one untested candidate mechanism. That mechanism is now refuted and a
better-supported one is identified and quantified.

**One new limitation is created.** The bounded-metric confound in Section 6 applies to AUROC as the
score and to `G` as a difference of means. It is a property of this project's chosen outcome measure,
not of CV-variance diagnostics in general, and any claim about `G` must now carry it.

## 8. Limitations specific to Study 4

- Groups A, B and C are pooled. Study 4 inherits no untouched holdout and claims none: all 25
  datasets had been scored under Study 2 before this study was designed.
- 19 of 25 datasets are estimable; the effective sample behind every interval is those 19 clusters,
  not 525 runs.
- Only one estimator *family* was tested — repeated stratified k-fold at the same k. A genuinely
  nested scheme in the full sense of Bates, Hastie and Tibshirani was not implemented, so the result
  bounds the naive estimator's precision, not every possible variance estimator.
- Model selection was frozen to Study 2's choice by design. Whether re-selecting under repeated CV
  would change which model is chosen, and therefore the outcome, is not tested here.
- Section 6 is post-hoc.
