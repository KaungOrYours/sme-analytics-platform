# Study 3 results — 2026-10-21

Pre-registered in `docs/study3_protocol.md` before any threshold was fitted. 693 runs in total:
525 from Study 2 reused for RQ8 (no new runs needed), plus 168 new runs on the 8 transfer datasets.
0 skipped. Regenerate with `evaluation/recalibrate_study3.py` and
`evaluation/full_run_study3_transfer.py`.

## The holdout gap, and how it was closed

Verified by enumerating all 162 PMLB classification datasets: **no binary dataset with n <= 500
exists outside the 44 raw PMLBmini candidates.** PMLBmini is exhaustive for that criterion. Study 2
having spent all 25 of TabMini's curated survivors, no fresh in-regime sample exists, and the 19
TabMini excluded are off-limits (several on PII and ethical-sensitivity grounds this project is also
bound by; taking only the methodologically-excluded subset would make the curation argument
incoherent).

The gap was closed two ways that need no in-regime data: **leave-one-dataset-out** over the 25,
where every dataset is held out exactly once and every reported figure is out-of-sample; and an
**external transfer sample** of 8 untouched binary datasets at 500 < n <= 1000, used with a declared
population difference and never pooled with the 25.

## RQ8: recalibration fails. Study 2's Claim 2 is refuted

All figures out-of-sample. 525 runs, 25 datasets, 142 poor-optimism runs.

| Diagnostic | anchor t | anchor MCC | fitted t (median) | recalibrated MCC [95% CI] | gain |
|---|---|---|---|---|---|
| `n/p` | 10.0 | 0.238 | 11.54 | 0.246 [0.16, 0.32] | +0.008 |
| `EPV` | 10.0 | 0.156 | 6.67 | 0.161 [0.07, 0.24] | +0.005 |
| `sigma_cv` | 0.10 | 0.184 | 0.081 | 0.043 [-0.04, 0.13] | **-0.140** |
| `fold_contamination` | 0.10 | 0.185 | 0.199 | 0.192 [0.11, 0.28] | +0.007 |
| `evalml_cov` | 0.20 | 0.232 | 0.221 | 0.158 [0.06, 0.26] | **-0.074** |
| `evalml_range` | 0.50 | 0.104 | 0.055 | **-0.057** [-0.14, 0.03] | **-0.161** |

**Fitting the threshold optimally on 24 datasets makes it worse on the 25th in three of six cases,
and gains nothing in the other three.** `P7 is refuted`: `evalml_range` and `EPV`, the two Study 2
identified as specifically miscalibrated, did not improve — `evalml_range` collapsed from a weak
positive to negative.

The mechanism is visible in the spread of fitted thresholds across the 25 folds:

| Diagnostic | fitted-threshold range across folds |
|---|---|
| `sigma_cv` | [0.0139, 0.1394] — a tenfold span |
| `evalml_range` | [0.0528, 0.4020] — an eightfold span |
| `evalml_cov` | [0.0161, 0.4095] — a twenty-fivefold span |
| `EPV` | [3.31, 7.35] |
| `n/p` | [10.12, 14.22] |

**The optimal threshold is itself sample-dependent.** Leaving out one dataset of 25 moves the
MCC-maximising cut by up to an order of magnitude. A threshold fitted on one sample is therefore
not a property of the diagnostic; it is a property of the sample, which is precisely why it fails
out-of-sample.

**`P10 is confirmed.** `n/p`'s out-of-sample MCC across all 25 held-out datasets is 0.246, against
the +0.540 it scored on Study 2's single Group C. The strong Group C result was a favourable sample,
exactly as predicted from Study 2 Finding 3's instability.

**`P8` requires care rather than a verdict.** `fold_contamination`'s out-of-sample MCC is positive
(0.192), which looks like survival. It is not: RQ8 is pooled across corruption families by design
(a deployed diagnostic cannot know which corruption is present), and Study 2 Finding 4 established
that this diagnostic's pooled figures are confounded — it is substantially a detector for "duplicates
were injected," inheriting discrimination from the higher poor rate in that condition. Its
within-family AUROC is below 0.5 on both Study 2's Group C and this study's transfer sample. The
pooled positive is the confound, not a result, and recalibration did not change it (+0.007).

## RQ9: the signal transfers, the thresholds do not

8 untouched datasets, 500 < n <= 1000, 168 runs. Thresholds fitted on the 25 small datasets and
applied unchanged.

**First, a clean confirmatory result on base rate.** Only 9 of 168 runs (5.4%) are poor-optimism,
against 22.2% on Study 2's Group C and 41.3% on Group B. Larger n produces far fewer
validation-to-test optimism failures, independently reproducing the direction of Study 1's
Experiment 4 (where halving training data multiplied the poor rate roughly sevenfold).

With 9 positive cases the binary MCCs are mostly degenerate and near-uninformative:

| Diagnostic | fitted t | MCC [95% CI] | anchor MCC |
|---|---|---|---|
| `n/p` | 11.54 | 0.000 (degenerate) | 0.000 |
| `EPV` | 6.67 | -0.074 [-0.11, -0.05] | -0.090 |
| `sigma_cv` | 0.081 | -0.037 [-0.06, -0.01] | 0.000 |
| `evalml_cov` | 0.221 | 0.000 (degenerate) | 0.000 |
| `evalml_range` | 0.055 | 0.197 [0.07, 0.30] | 0.000 |
| `fold_contamination` | 0.199 | 0.105 [-0.06, 0.26] | 0.154 |

**`P9` is refuted on MCC**: only `evalml_range` transfers positively, and `sigma_cv` and `EPV` go
slightly negative. But threshold-free, the picture is the opposite:

| Diagnostic (AUROC) | pooled | clean | missing | duplicates | outliers |
|---|---|---|---|---|---|
| `EPV` (negated) | 0.725 | 0.826 | 0.826 | 0.821 | degenerate |
| `evalml_range` | 0.710 | 0.826 | 0.554 | 1.000 | degenerate |
| `sigma_cv` | 0.696 | 0.826 | 0.533 | 1.000 | degenerate |
| `evalml_cov` | 0.692 | 0.913 | 0.598 | 1.000 | degenerate |
| `n/p` (negated) | 0.585 | 0.696 | 0.696 | 0.714 | degenerate |
| `fold_contamination` | 0.584 | **0.239** | **0.359** | **0.266** | degenerate |

The cross-validation-variance diagnostics retain positive ranking signal (0.69 to 0.71 pooled) on a
population with twice the sample size and a quarter the failure rate, while their thresholded
decisions collapse to zero. `fold_contamination` again anti-predicts within every family,
independently reproducing its Study 2 refutation on a different population.

The outlier family is degenerate here because it contains no poor-optimism runs at all —
independently reproducing Study 2 Finding 2, that outlier corruption pushes `G` negative and is
structurally invisible to a one-sided optimism label.

## What the three studies jointly establish

Stated as the corrected pair of claims. Study 2's Claim 2 as originally written is withdrawn.

**Claim 1 (unchanged, strengthened again).** Low-overhead cross-validation-variance diagnostics
carry genuine predictive signal for automated-pipeline validation-to-test optimism. Threshold-free
AUROC 0.69 to 0.86 within every corruption family, on Study 2's pre-registered untouched holdout,
replicated on Study 2's Group B, and now reproduced on a larger-n population outside the original
regime. Study 1's negative conclusion was an artifact of having three poor-labelled runs per group.

**Claim 2 (corrected, and stronger than the version it replaces).** That signal cannot be converted
into a fixed global threshold that generalises across dataset samples. Demonstrated three
independent ways: the vendor's own shipped threshold discards it (`evalml_range` fires on 6 to 16%
of runs while carrying competitive signal); frozen literature-anchored thresholds achieve MCC in the
0.10 to 0.24 band at best; and thresholds fitted optimally by leave-one-dataset-out generalise
*worse* than the anchors, because the MCC-maximising cut moves by up to an order of magnitude when
one dataset of 25 is exchanged. The diagnostics are informative as **relative rankings** and
unreliable as **absolute warnings**.

This is a negative result about an entire class of deployable warning, and it has a direct
consequence the pre-registration committed to reporting: it points back toward the per-instance
trained estimators that this project positioned itself against (Lahoti, Gummadi and Weikum, 2023).
If no fixed cut generalises, something that adapts per dataset — a learned estimator, or a
relative/within-dataset calibration — is the remaining option. Study 3 therefore partially
*vindicates* that literature rather than displacing it, which is a more defensible position than
the one Study 2 was heading toward.

## Limitations

- RQ9 rests on 9 poor-labelled runs. Its MCC figures are near-uninformative and its AUROC figures
  carry wide implicit uncertainty; the transfer conclusion is directional, not confident.
- RQ8's bootstrap resamples runs, not datasets, while the fitting procedure is dataset-level. The
  interval therefore understates uncertainty in the threshold itself.
- Fitting maximised MCC; a different criterion (Youden's J, cost-weighted) could place thresholds
  differently. Only MCC was pre-registered, and only MCC was run.
- **Not tested, and the clear next step:** relative or within-dataset calibration — for example
  flagging the worst-ranking fraction of runs for a given dataset rather than applying an absolute
  cut. Claim 2 establishes that absolute thresholds fail; it does not establish that no deployable
  rule exists. That study would need its own pre-registration and a fresh population, which, per
  the first section, no longer exists in-regime.
