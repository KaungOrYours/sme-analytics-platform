# Stratified re-analysis — between-dataset versus within-dataset discrimination

**Written 2026-10-22. POST-HOC. Not pre-registered.**

Studies 2 and 3 were pre-registered before they ran. This re-analysis was not. It was written in
response to an external critical review of the project's documents dated 22 October 2026, which
asked whether the diagnostics' reported discrimination answers *"is this dataset risky?"* or
*"will this run disappoint?"* — and pointed out those are not the same product.

**No new pipeline runs were produced.** Every number below re-analyses run records already
collected under the Study 2 and Study 3 protocols. Code: `evaluation/score_stratified.py`.
Outputs: `evaluation/results/{study2_B,study2_C,study3_transfer}_stratified_scores.json`.

The answer changes one of the project's two headline claims. It is reported here in full, including
the part that weakens the project's own position.

---

## 1. Why this analysis exists

Study 2 Finding 5 established that pooling across injected corruption conditions is confounded: a
diagnostic correlated with the injected condition inherits discrimination it did not earn. That
finding was acted on — every subsequent figure was reported within corruption family.

The same argument applies to **dataset identity**, and it was not acted on. Runs are not
exchangeable: each source dataset contributes 21 runs, and failure rates are extremely clustered by
dataset. In Study 2 Group C the per-dataset poor counts are 0, 0, 0, 1, 1, 6, 9, 10 and 15 out of 21.
A diagnostic that merely identifies *which dataset* a run came from would therefore score well on a
pooled figure without being able to order runs within any dataset.

Study 2 caught this confound for corruption family and missed it for dataset. This document closes
that gap.

## 2. Method

**Stratified concordance.** The probability that a diagnostic ranks a poor-labelled run above a
non-poor run, *computed only over pairs sharing a stratum*, ties counted as 0.5. With a single
stratum this is exactly AUROC, so the "pooled" column reproduces the published tables. Narrowing the
stratum progressively removes between-stratum ordering:

| Stratum | What stays free to vary | What it answers |
|---|---|---|
| pooled | everything | the published AUROC |
| corruption family | dataset, rate, seed | Study 2 Finding 5's correction |
| dataset | family, rate, seed | can it order runs inside one dataset? |
| dataset x family | rate, seed | ...controlling for the injected condition too |
| dataset x family x rate | seed only | ...with nothing left but the random seed |

**Dataset-clustered bootstrap.** All intervals resample whole source datasets with replacement
(every run of a dataset travels together), 2000 resamples, seed 0. Studies 1–3 resampled *runs*,
which treats 21 correlated runs as 21 independent observations. The cluster unit here matches the
unit the transfer claims are about. A dataset drawn twice is re-keyed into two separate strata so it
forms two clusters rather than one double-sized one.

**Explicit NA accounting.** A stratum containing only one outcome class cannot order anything; it is
undefined, excluded, and counted — never scored as zero. The script reports how many datasets contain
both classes, warns when that count is below three, and marks zero-width intervals as `degenerate`
rather than letting them read as precision.

## 3. Reproducibility check (an opening closed in passing)

The threshold-free AUROC tables in `study2_results.md` and `study3_results.md` were computed inline
during those sessions and never committed as code — an examiner asking "show me what produced this
table" would have found nothing.

`score_stratified.py` recomputes them from the raw run records. **All 48 published figures checked
reproduce exactly to 3 d.p.** — 30 from Study 2 Group C's table (6 diagnostics x pooled + 4 corruption
families) and 18 from Study 3's transfer tables (6 diagnostics x pooled + clean + duplicates).
The published measurements were correct. What follows revises what they *mean*, not what they are.

## 4. Results

Point estimate with 95% dataset-clustered CI.

### Study 2 Group C (pre-registered confirmation group; 9 datasets, 189 runs, 42 poor)

| Diagnostic | pooled (published) | within-family | within-dataset | within ds x family | + rate (seed only) |
|---|---|---|---|---|---|
| `sigma_cv` | 0.706 [0.43, 0.88] | 0.783 [0.52, 0.92] | 0.253 [0.07, 0.45] | 0.273 [0.07, 0.56] | 0.263 [0.05, 0.58] |
| `evalml_cov` | 0.711 [0.40, 0.88] | 0.792 [0.51, 0.93] | 0.174 [0.06, 0.28] | 0.208 [0.04, 0.38] | 0.184 [0.00, 0.40] |
| `evalml_range` | 0.694 [0.42, 0.87] | 0.773 [0.49, 0.92] | 0.247 [0.07, 0.48] | 0.240 [0.00, 0.60] | 0.224 [0.00, 0.63] |
| `EPV` (negated) | 0.741 [0.36, 0.89] | 0.763 [0.40, 0.90] | 0.279 [0.04, 0.39] | 0.435 [0.30, 0.48] | 0.487 [0.41, 0.58] |
| `n/p` (negated) | 0.742 [0.35, 0.89] | 0.763 [0.40, 0.90] | 0.274 [0.05, 0.38] | 0.442 [0.20, 0.49] | 0.500 (degenerate) |
| `fold_contamination` | 0.574 [0.44, 0.80] | 0.413 [0.26, 0.55] | 0.723 [0.62, 0.94] | 0.539 [0.48, 0.67] | 0.461 [0.31, 0.53] |

| Diagnostic | distinct values per dataset | within-dataset variance share | between-dataset Spearman rho |
|---|---|---|---|
| `sigma_cv` | 19.0 | 0.346 | +0.936 |
| `evalml_cov` | 19.1 | 0.346 | +0.877 |
| `evalml_range` | 16.3 | 0.352 | +0.877 |
| `EPV` (negated) | 5.3 | 0.019 | +0.596 |
| `n/p` (negated) | 3.0 | 0.023 | +0.596 |
| `fold_contamination` | 8.8 | 0.799 | +0.238 |

### Study 2 Group B (exploratory; 9 datasets, 189 runs, 78 poor)

| Diagnostic | pooled (published) | within-family | within-dataset | within ds x family | + rate (seed only) |
|---|---|---|---|---|---|
| `sigma_cv` | 0.656 [0.51, 0.77] | 0.730 [0.59, 0.83] | 0.429 [0.37, 0.48] | 0.474 [0.40, 0.54] | 0.486 [0.39, 0.57] |
| `evalml_cov` | 0.638 [0.46, 0.77] | 0.732 [0.56, 0.85] | 0.360 [0.28, 0.43] | 0.431 [0.34, 0.51] | 0.472 [0.38, 0.55] |
| `evalml_range` | 0.660 [0.51, 0.77] | 0.740 [0.60, 0.84] | 0.435 [0.37, 0.50] | 0.493 [0.41, 0.56] | 0.500 [0.40, 0.59] |
| `EPV` (negated) | 0.590 [0.40, 0.76] | 0.617 [0.42, 0.81] | 0.357 [0.29, 0.43] | 0.474 [0.44, 0.50] | 0.514 [0.47, 0.55] |
| `n/p` (negated) | 0.535 [0.35, 0.69] | 0.554 [0.35, 0.73] | 0.356 [0.29, 0.42] | 0.467 [0.43, 0.50] | 0.500 (degenerate) |
| `fold_contamination` | 0.638 [0.56, 0.71] | 0.582 [0.48, 0.70] | 0.643 [0.55, 0.73] | 0.485 [0.43, 0.55] | 0.410 [0.35, 0.48] |

Between-dataset Spearman rho: `sigma_cv` +0.883, `evalml_cov` +0.900, `evalml_range` +0.933,
`EPV` +0.367, `n/p` +0.183, `fold_contamination` +0.452.

### Study 3 transfer (8 datasets, 168 runs, 9 poor)

| Diagnostic | pooled (published) | within-family | within-dataset |
|---|---|---|---|
| `sigma_cv` | 0.696 [0.56, 0.78] | 0.872 [0.80, 0.92] | 0.259 (degenerate) |
| `evalml_cov` | 0.692 [0.53, 0.78] | 0.894 [0.82, 0.93] | 0.139 (degenerate) |
| `evalml_range` | 0.710 [0.58, 0.79] | 0.877 [0.81, 0.92] | 0.296 (degenerate) |
| `EPV` (negated) | 0.725 [0.44, 0.93] | 0.823 [0.54, 0.99] | 0.167 (degenerate) |
| `n/p` (negated) | 0.585 [0.29, 0.81] | 0.708 [0.34, 0.99] | 0.167 (degenerate) |
| `fold_contamination` | 0.584 [0.51, 0.69] | 0.287 [0.13, 0.48] | 0.833 (degenerate) |

## 5. What the numbers say

**(1) The published discrimination is between-dataset ordering.** For the three cross-validation-
variance diagnostics, Group C concordance drops from 0.694–0.711 pooled and 0.773–0.792 within-family to 0.174–0.253
within dataset, and those within-dataset intervals sit entirely below 0.5. Across all three samples
the within-dataset range is 0.139–0.435 against 0.730–0.894 within-family. The
between-dataset Spearman correlations are +0.88 to +0.94 — these diagnostics rank *datasets* by
failure rate almost perfectly. They are dataset-risk indicators, not run-risk indicators.

**(2) It is not an artefact of the injected condition.** Holding dataset, corruption family and
corruption rate all fixed, so that only the random seed varies, Group C's `sigma_cv` concordance is
0.263 [0.05, 0.58] — essentially unchanged from the within-dataset figure. The reversal survives the
strictest available control.

**(3) Within a dataset the association runs backwards.** Below 0.5 is not merely "no signal": inside
a dataset, *higher* cross-validation variance is associated with *less* validation-to-test optimism.
The effect is consistent across all three CV-variance diagnostics, both Study 2 groups and the
transfer sample. The mechanism is not established here and should be stated as an open question, not
explained away. One plausible account worth testing: `G = S_CV − S_test` and `sigma_cv` are computed
from the same fold scores, so within a fixed dataset the sampling noise that inflates one can deflate
the other.

**(4) `n/p` cannot discriminate within a dataset, by construction.** It takes exactly 3.0 distinct
values per dataset (clean, +15% duplicates, +35% duplicates), carries 2.3% of its variance within
dataset, and is literally constant once dataset, family and rate are fixed — hence the exactly 0.500
degenerate cell. Its pooled 0.742 on Group C is entirely between-dataset ordering. `EPV` behaves the
same way (1.9% within-dataset variance).

**(5) `fold_contamination` is the exact mirror image, and this sharpens its refutation.** It is the
one diagnostic with high within-dataset variance (79.9% on Group C) and above-chance within-dataset
concordance (0.723), while its *within-family* figure is below chance (0.413). Study 2 refuted it as
a corruption-family detector. The fuller statement: it is the only diagnostic that tracks something
run-level, but what it tracks is which corruption was applied, not whether that run failed.

**(6) Clustered intervals are much wider than the published run-level ones.** Group C's `sigma_cv`
pooled concordance is 0.706 with a clustered CI of [0.43, 0.88] — **it crosses 0.5.** The headline
threshold-free result is not statistically distinguishable from chance once the 189 runs are counted
as the 9 datasets they actually are.

**(7) Study 3's transfer claim rests on a single dataset.** All 9 poor-labelled runs in the 168-run
transfer sample come from `profb`; the other seven datasets have zero. Only 2 of 32 dataset x family
cells contain both outcome classes. 36% of bootstrap resamples (715 of 2000) contain no positive case
at all, so the reported transfer intervals are *conditional on drawing `profb`* and are narrower than
the honest unconditional interval. "The signal transfers to a larger-n population" is not supportable
from this evidence; what was observed is that one dataset out of eight was correctly ranked as the
risky one.

## 6. What this changes

Claim 1 as previously written — "the diagnostics carry genuine predictive signal for
validation-to-test optimism" — is **too strong and insufficiently specific**. It should become:

> These diagnostics carry information about **which dataset** is at risk of validation-to-test
> optimism, and essentially none about **which run** within a dataset will disappoint. Even the
> between-dataset signal is measured on 8–9 independent datasets per group and its clustered
> interval includes chance.

Claim 2 — no fixed global threshold generalises — **survives, and gains a mechanism.** If the signal
lives at the dataset level, then a run-level quantity's scale is set by the dataset it came from, and
a global cut has nothing stable to cut on. Study 3's finding that the MCC-optimal threshold moves by
an order of magnitude when one dataset is exchanged is exactly what this predicts. The two claims now
explain each other rather than sitting side by side.

This also answers the "is `sigma_CV` just mechanically coupled to `G`?" objection, though not in the
project's favour: a purely mechanical coupling would show up *within* dataset, which is precisely
where the positive signal is absent.

## 7. Limitations of this re-analysis

- **Post-hoc.** Not pre-registered, run after seeing the earlier results, motivated by an external
  critique. It is evidence for revising a claim, not independent confirmation of a new one.
- Within-dataset strata are small: 77 comparable pairs across 14 estimable strata on Group C, 10 pairs
  across 2 strata on transfer. The *direction* is consistent across 6 diagnostics x 3 samples, which
  is why it is reported as a finding; individual cells are not individually reliable.
- Dataset-clustered bootstrap with 8–9 clusters is itself low-powered. Wide intervals here mean
  "this study cannot tell", not "the effect is absent".
- Concordance is pair-weighted, so larger strata dominate. A stratum-unweighted average was computed
  during development and gave the same direction; only the pair-weighted figure is reported.
- Only `poor_optimism` is scored, matching Studies 1–3. The two-sided labels were not re-analysed.
- The reversal in (3) is reported as an observation with an untested candidate mechanism, not an
  explained result.

## 8. Open actions this raises

1. The FPR must present discrimination as between-dataset, with the within-dataset null beside it.
   A results chapter reporting only the pooled AUROC would not survive this re-analysis.
2. Any future "does it transfer" study needs its holdout checked for *estimable clusters*, not just
   run count — Study 3's transfer sample looked like 168 runs and was worth one dataset.
3. The within-dataset reversal in (3) deserves its own pre-registered test, with the shared-fold-noise
   mechanism stated as the hypothesis in advance.
