# Study 4 protocol — does the per-run null survive a better variance estimator?

**PRE-REGISTERED 2026-10-23. Committed before any run.**

This file is committed **on its own, before any Study 4 code is executed and before any Study 4
result exists**. Studies 2 and 3 committed their protocols alongside their results, so git could not
prove the freeze (`docs/findings.md` section 8). This commit is the correction; its position in
history is part of the evidence.

Motivation is stated honestly up front: **this study is reactive.** It exists because of a specific
objection to results the project already published, set out in `docs/study4_candidates.md`. The
hypotheses and analysis below are pre-registered, but the question was prompted by a known weakness
rather than discovered independently, and that is a weaker position than a question posed before any
data existed. It is the same distinction already drawn for Correction 3.

## 1. Background and the objection being answered

The project's current position is that cross-validation-variance diagnostics rank *datasets* by
optimism risk (between-dataset Spearman rho +0.88 to +0.94) and carry no usable *within-dataset,
per-run* discrimination (0.14 to 0.44, intervals at or below chance), and that the failure of any
fixed global threshold follows from this.

Every one of those figures rests on a diagnostic that is **the standard deviation of five numbers**.
Verified in source, not assumed: `evaluation/diagnostics.py:64` computes `cv_scores_for_model` with a
single `StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)`, and `sigma_cv` is
`best_scores.std(ddof=1)` over those five values. The same five values also produce
`s_cv_selected`, and therefore `G = s_cv_selected - s_test`.

The objection is therefore: *the per-run null may be a property of the estimator, not of the
estimand.* A five-sample standard deviation is a very noisy estimate, and attenuation from
measurement error in a predictor biases its measured discrimination toward chance.

This objection must be taken seriously because **the project has already made this exact mistake
once.** Correction 1 withdrew Study 1's "`sigma_CV` has no discriminative value" because it rested
on three positive cases per group. Correction 3's within-dataset null has not been subjected to the
equivalent check.

Two established results make the objection concrete rather than rhetorical. Bengio and Grandvalet
(2004) prove there is no universally unbiased estimator of the variance of k-fold cross-validation,
and that naive estimators ignoring the correlation induced by overlapping training sets can grossly
underestimate it. Bates, Hastie and Tibshirani (JASA, DOI 10.1080/01621459.2023.2197686) show that
cross-validation approximates the average error over the population of training sets rather than the
error of the particular fitted model, and propose a nested scheme targeting the latter. **Both are
flagged UNREAD by the student and neither may be cited in the FPR until read** (the standing rule in
`docs/literature_matrix.md`). They are recorded here because the design is motivated by them.

## 2. Research questions

**RQ10 (primary).** Does the absence of within-dataset discrimination survive a variance estimator
with substantially greater precision than the shipped single five-fold standard deviation?

**RQ11 (secondary).** Is the consistently *sub-chance* within-dataset concordance an artefact of
`sigma_CV` and `G` being computed from the same fold scores?

## 3. What is held fixed

Only the variance estimator varies. Everything else is frozen at Study 2's values so that any change
in measured discrimination is attributable to estimation precision alone:

- **The outcome label is frozen and unchanged.** Study 4 uses Study 2's existing `poor_optimism`
  label at `delta_G = 0.05`, computed from Study 2's original `G`. The outcome is not recomputed.
- **The dataset sample, splits, corruption and seeds are frozen.** `split_outer(df, "target", seed)`
  and the injectors are seed-deterministic, so each Study 2 run is reproduced exactly.
- **Model selection is frozen.** Each run re-fits the model Study 2 selected for it, recorded in
  `model_name`. Re-selecting under repeated CV would vary two things at once.
- **`build_preprocessor` is not touched.** It is imported by `evaluation/diagnostics.py` and the 861
  existing runs depend on it.

## 4. Estimators compared

All computed on the same training partition of the same run, for the same fitted model family.

| Id | Definition | Fits per run |
|---|---|---|
| `sigma_R1` | **As shipped.** One `StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)`; `std(ddof=1)` of the 5 fold scores | 5 |
| `sigma_R10` | Mean over 10 repeats of the per-repeat 5-fold `std(ddof=1)`, repeat seeds `1000..1009` | 50 |
| `sigma_R20` | Same at 20 repeats, repeat seeds `1000..1019` | 100 |
| `sigma_pooled20` | `std(ddof=1)` over all 100 fold scores from the 20 repeats, reported as a secondary definition | (reuses R20) |

`sigma_R10` and `sigma_R20` estimate **the same estimand as the shipped rule** — the standard
deviation of a 5-fold CV score vector — with 10x and 20x the data. `sigma_pooled20` estimates a
different, larger quantity (it absorbs between-repeat variation) and is reported separately so the
two are never conflated.

**Validation gate, to be passed before any Study 4 conclusion is drawn.** `sigma_R1` recomputed by
the Study 4 runner must reproduce Study 2's stored `sigma_cv` **exactly** for every run. If it does
not, the reproduction is wrong and no comparison is valid. This mirrors the reproduce-before-revise
check that validated `evaluation/score_stratified.py` against 48 published AUROC figures.

## 5. RQ11: the decoupled-G analysis

With 20 repeats available, define:

- `sigma_even` = mean per-repeat `std(ddof=1)` over the 10 even-indexed repeats;
- `G_decoupled` = (mean fold score over the 10 **odd**-indexed repeats) - `s_test`.

`sigma_even` and `G_decoupled` share no fold scores. If the sub-chance within-dataset concordance is
produced by shared sampling noise — noise inflating `sigma_CV` deflating `G`, and vice versa — then
concordance computed from the decoupled pair should rise to approximately 0.5 or above.

This analysis uses a **recomputed** outcome and is therefore **exploratory and clearly separated**
from RQ10, which uses the frozen label. It is reported as a mechanism probe, not as a headline.

## 6. Scope of runs

Study 2's full grid, all three dataset groups (A, B, C): 25 datasets x 7 conditions x 3 seeds = 525
runs, automated pipeline only, matching Study 2's pre-registered scoring scope. Group C carries no
special status here: it was already unsealed and scored under Study 2, so Study 4 inherits no
untouched holdout and **claims none**.

Measured cost on `bupa` (n=345, p=5): single 5-fold 183 ms; R=10 is 9.4x and R=20 is 17.8x. Study 2's
525 runs took about 117 s, so the full Study 4 grid is expected to take roughly 35 to 45 minutes.

## 7. Analysis plan

Scoring reuses `evaluation/score_stratified.py` unchanged: stratified concordance at pooled,
within-family, within-dataset, within-dataset-x-family and within-dataset-x-family-x-rate nestings;
**dataset-clustered bootstrap** (2000 resamples, whole datasets resampled, seed 0); estimable-cluster
accounting with NA flags for degenerate cells.

Headline comparison: **within-dataset concordance and its dataset-clustered interval, for `sigma_R1`
against `sigma_R10` and `sigma_R20`**, reported within corruption family, never pooled across
families (Study 2 Finding 5 established that pooling across injected conditions confers unearned
discrimination).

Between-dataset Spearman rho is reported for each estimator as a control.

## 8. Pre-registered predictions

**P11 (estimator-artefact hypothesis).** If the per-run null is caused by estimator imprecision,
within-dataset concordance rises monotonically with R, and at R=20 its dataset-clustered interval
excludes 0.5 from below in at least the `missing_values` and `duplicates` families — the two with
enough poor-labelled runs to estimate anything.

**P12 (estimand hypothesis).** If the null is a property of the quantity rather than its estimate,
within-dataset concordance at R=10 and R=20 stays inside Study 2's observed 0.139 to 0.435 band, and
the R=20 interval does not exclude chance from below.

**P13 (control).** Between-dataset Spearman rho is substantially unchanged across R. The
dataset-level signal is strong and should not depend on estimator precision; if it moves materially,
the reproduction is suspect and Section 4's validation gate should be re-examined.

**P14 (RQ11, exploratory).** If shared fold noise explains the sub-chance result, concordance from
the decoupled pair (`sigma_even`, `G_decoupled`) is at least 0.5, materially above the coupled
within-dataset figures.

P11 and P12 are mutually exclusive on the stated criteria. An outcome satisfying neither — for
example a non-monotonic response to R, or intervals too wide to separate the two — is a third,
reportable result and is **not** to be presented as support for either.

## 9. What would make this a null result

Stated in advance so it cannot be reinterpreted later:

- Within-dataset concordance that moves with R but whose dataset-clustered intervals overlap both
  0.5 and the Study 2 figures is **uninformative**, not confirmation of P12. With 8 or 9 estimable
  clusters per group the intervals may simply be too wide to decide, and that must be said.
- If the validation gate in Section 4 fails, Study 4 reports the reproduction failure and nothing
  else.
- If `sigma_R20` and `sigma_R1` turn out to be near-identical per run (correlation above roughly
  0.95), then the extra repeats changed nothing measurable, the comparison has no power to separate
  the hypotheses, and that is the finding. It would also be a result worth stating: it would mean
  the shipped estimator is not meaningfully noisy at this scale.

## 10. Consequences, both ways

**If P11 holds**, Contribution 1 narrows a third time: the signal is present per run but the shipped
estimator is too crude to recover it. The practical recommendation becomes concrete — a vendor
thresholding a five-fold standard deviation should spend more compute on the estimate. This would be
the project's **fourth** self-correction and must be presented as such.

**If P12 holds**, Contribution 1 is strengthened: the per-run null survives a tenfold to twentyfold
increase in estimation precision, which answers the strongest available objection and promotes the
claim from "no signal was found" to "no signal is recoverable at this granularity by this class of
estimator."

Neither outcome changes Contribution 2, which rests on threshold transfer and is already established
three independent ways.

## 11. Reporting commitments

- Results go in `docs/study4_results.md`, with the status of each of P11 to P14 stated explicitly,
  including any that are refuted.
- Refuted predictions are retained, as in Studies 2 and 3. Four of Study 2's six predictions were
  refuted or only partially supported and all remain in its record.
- The reactive motivation stated in the preamble is repeated wherever the result is reported.
- `docs/findings.md` is updated to reflect the outcome, and remains the single authoritative
  position.
