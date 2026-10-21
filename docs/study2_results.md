# Study 2 results — 2026-10-21

Pre-registered in `docs/study2_protocol.md` before any run; Amendment 1 recorded after Group B was
scored and before Group C was executed. 525 runs total (Group A 147, B 189, C 189), 0 skipped,
~117s total wall-clock. Scope: automated-pipeline runs only, carried forward from Study 1.
Regenerate with `evaluation/full_run_study2.py` and `evaluation/score_study2.py`.

Group A (7 datasets) is Study 1's spent sample and carries no confirmatory weight. Group B (9 fresh
datasets) is the exploratory/rule-selection group. **Group C (9 datasets) is the confirmation
holdout, run once, with every threshold exactly as frozen.**

## Headline: Study 1's central negative finding does not replicate

Study 1 concluded that `sigma_CV > 0.10` provides no positive discrimination, with bootstrap MCC
intervals excluding positive values on both of its groups ([-0.25, 0.00] and [-0.26, 0.00]). That
conclusion does not survive a larger sample.

| Group | n runs | poor_optimism | `sigma_cv` MCC [95% CI] |
|---|---|---|---|
| Study 1 development | 36 | 3 (8.3%) | -0.148 [-0.25, 0.00] |
| Study 1 final-evaluation | 27 | 3 (11.1%) | -0.147 [-0.26, 0.00] |
| **Study 2 Group B** | 189 | 78 (41.3%) | **+0.180 [0.04, 0.32]** |
| **Study 2 Group C (confirmation)** | 189 | 42 (22.2%) | **+0.262 [0.12, 0.40]** |

The most likely explanation is power. Study 1 had 3 poor-labelled runs per group; Study 2 has 78 and
42. A diagnostic cannot be shown to discriminate against three positive cases, and Study 1's own
write-up flagged its intervals as wide — but it stated the negative direction as the confident
finding. **That framing must be corrected in the FPR.** Study 1's numbers are not wrong; the
inference drawn from them was over-confident, and a larger sample reverses the sign.

## Threshold-free discrimination, within corruption family (Group C, confirmation)

AUROC of each diagnostic's underlying value against `poor_optimism`, oriented so higher means more
predicted risk. Threshold-free, so it measures signal independently of calibration (Amendment 1).

| Diagnostic | pooled | clean | missing | duplicates | outliers | P5 (>0.6 all families) |
|---|---|---|---|---|---|---|
| `n/p` (negated) | 0.742 | 0.936 | 0.870 | 0.649 | 0.810 | PASS |
| `EPV` (negated) | 0.741 | 0.936 | 0.870 | 0.649 | 0.810 | PASS |
| `sigma_cv` | 0.706 | 0.727 | 0.807 | 0.746 | 0.848 | **PASS** |
| `evalml_cov` | 0.711 | 0.745 | 0.800 | 0.760 | 0.863 | **PASS** |
| `evalml_range` | 0.694 | 0.727 | 0.777 | 0.746 | 0.840 | **PASS** |
| `fold_contamination` | 0.574 | 0.341 | 0.400 | 0.441 | 0.394 | **FAIL** |

**P5 is confirmed** for the three cross-validation-variance diagnostics: each discriminates in every
corruption family on an untouched holdout, and the same ordering held on Group B
(`sigma_cv` 0.648/0.731/0.727/0.753, `evalml_cov` 0.642/0.711/0.719/0.789,
`evalml_range` 0.619/0.750/0.742/0.759). Two independent 9-dataset groups, one of them never
inspected before the frozen analysis, agree.

## Finding 2: the failure is threshold calibration, not the underlying signal

This is the sharper contribution, and it is visible only because Amendment 1 separated signal from
calibration.

| Diagnostic (Group C) | threshold-free AUROC | binary MCC at frozen threshold | fires on |
|---|---|---|---|
| `evalml_range >= 0.5` (EvalML's shipped rule) | 0.694 | 0.081 [-0.07, 0.24] | 30/189 (15.9%) |
| `EPV < 10` | 0.741 | 0.141 [0.01, 0.26] | 135/189 (71.4%) |
| `n/p < 10` | 0.742 | 0.540 [0.41, 0.66] | 63/189 (33.3%) |

`n/p` and `EPV` have **effectively identical threshold-free signal** on Group C — 0.742 against
0.741, and identical to three decimals within every family — yet their binary MCCs differ by a
factor of nearly four. The entire difference is where the threshold sits: `EPV < 10` fires on 71% of
runs and accumulates 100 false positives against 35 true ones. `EPV` is not a worse diagnostic than
`n/p`; it is the same information behind a badly placed cut.

`evalml_range` is the same story applied to shipped software. Its threshold-free AUROC (0.694) is
competitive with every other diagnostic here, but EvalML's own threshold — fold-score range >= 50%
of the metric's full range, which for AUROC means >= 0.5 — is so high that it fires on 6.3% of
Group B runs and 15.9% of Group C runs, and its binary MCC interval crosses zero. **The shipped
high-variance warning measures the right quantity and sets the bar far too high for small tabular
data.** That is a specific, actionable claim about production software, and a materially different
claim from "the warning has no predictive validity."

P6 as pre-registered required the firing rate to be under 10% on Group C; it was 15.9%, so **P6 is
only partially supported.** The firing rate is reported as measured rather than as predicted. The
substantive half — strong threshold-free signal, near-zero binary discrimination — holds.

## Finding 3: `n/p` is unstable across dataset samples, and that indicts single-group validation

`n/p < 10`'s binary MCC across five independently scored groups:

| Group | `n/p` MCC |
|---|---|
| Study 1 development (missing values) | +0.29 |
| Study 1 final-evaluation (missing values) | +0.50 |
| Study 1 final-evaluation (duplicates) | -0.322 |
| Study 2 Group B | -0.004 |
| Study 2 Group C (confirmation) | **+0.540** |

The same diagnostic, at the same frozen threshold, ranges from strongly positive to confidently
negative depending on which datasets are sampled. On Group B it is indistinguishable from no skill;
on Group C it is the strongest diagnostic measured. **No single-group evaluation of a diagnostic of
this kind is trustworthy**, which is a direct criticism of this project's own Study 1 design and of
any published validation resting on one benchmark sample.

## Finding 4: a pre-registered diagnostic of my own design, refuted

`fold_contamination` was built specifically for the failure mode Study 1 identified as dominant:
duplicated rows straddling a cross-validation fold boundary. **P2 is refuted.**

Two separate problems, both found rather than argued around:

1. **Confounding (Group B).** At its frozen threshold the diagnostic fires on 54 of 54
   duplicate-condition runs and 0 of 108 missing-value and outlier runs. It is a detector for
   "duplicates were injected," and its apparently respectable pooled MCC of 0.211 is inherited
   entirely from duplicate-condition runs having a higher poor rate (0.574 against 0.315-0.407).
   Within the duplicates family it is fully degenerate.
2. **Anti-prediction (Group C).** Threshold-free, its AUROC is below 0.5 in every corruption family
   (0.341 / 0.400 / 0.441 / 0.394). It does not merely fail to predict optimism; it weakly predicts
   its absence. Against `poor_pessimism` its MCC is -0.225 [-0.37, -0.10], confirming a consistent
   directional anti-association rather than noise.

The mechanism that motivated it is real — Study 1 established that duplicate corruption genuinely
inflates CV scores — but measuring fold contamination directly does not predict *which* runs it
harms. Contamination is near-universal once duplicates exist, so it has no variance left to
discriminate with.

A property of the data compounds this and was anticipated in Section 5 of the protocol: in
low-cardinality discrete feature spaces, duplicate rows are arithmetically unavoidable. `mux6` has 6
binary features and n=128, so only 64 distinct feature vectors exist; `corral` is similar. The
declared `forces_duplication` stratification turned out to be empty on Group B (0 of 189 runs) since
all such datasets fell into Groups A and C — reported as measured, not quietly dropped.

## Finding 5 (methodological): pooled scoring across injected conditions is confounded

Generalising Finding 4's first problem: in any design where corruption is injected, a diagnostic
correlated with the injected condition inherits discrimination it did not earn. Study 1 reported
per-family figures but never tested whether a diagnostic was confounded with the condition itself.
Every figure in this document is therefore reported within corruption family as well as pooled, and
no pooled figure is quoted without its breakdown. This is a constraint on how such evaluations must
be designed, not a quirk of one diagnostic.

## Status of each pre-registered prediction

| Prediction | Outcome |
|---|---|
| P1 — `EPV` beats `n/p` by MCC on Group C | **Refuted.** 0.141 against 0.540. Identical threshold-free signal; `EPV`'s threshold is badly placed |
| P2 — `fold_contamination` positive under duplicates, beats `n/p` and `sigma_cv` there | **Refuted.** Degenerate within family on B; AUROC < 0.5 in every family on C |
| P3 — `evalml_range` fires rarely; `evalml_cov` not positively discriminating | **Split.** Rare firing confirmed (6.3% / 15.9%). The `evalml_cov` half is refuted: MCC +0.250 [0.11, 0.39] on B and +0.248 [0.08, 0.41] on C |
| P4 — pessimism base rate higher under outliers; some diagnostic positive on pessimism | **Partially supported.** Outlier pessimism rates are high (B 24/54, C confirms the pattern) but no diagnostic achieves a positive MCC with a CI excluding zero against `poor_pessimism` on C |
| P5 — three CV-variance diagnostics > 0.6 AUROC in every family; `n/p` and `fold_contamination` not | **Confirmed for the three.** `fold_contamination` fails as predicted; `n/p` passes on C, unlike on B (see Finding 3) |
| P6 — `evalml_range`: strong signal, fires < 10% | **Partially supported.** Signal confirmed, binary MCC near zero; firing rate 15.9% on C, above the predicted bound |

Four of six predictions were refuted or only partially supported, including both diagnostics
designed for this study. The two that survived are the ones the FPR should lead with.

## What this means for the two novelty claims

**Claim 1 (strengthened, and now positive).** Low-overhead cross-validation-variance diagnostics do
carry genuine predictive validity for automated-pipeline validation-to-test optimism on small
tabular data — AUROC 0.69 to 0.86 within every corruption family, on a pre-registered untouched
holdout, replicated across two independent dataset groups. This is a stronger result than Study 1's
negative one, and it corrects Study 1 rather than merely extending it.

**Claim 2 (new).** What fails in practice is threshold calibration, not the diagnostics' construct.
Demonstrated three ways: a shipped vendor threshold (`evalml_range`) that discards a competitive
signal by firing almost never; two diagnostics with statistically indistinguishable signal
(`n/p`, `EPV`) whose binary performance differs fourfold purely through threshold placement; and a
diagnostic whose binary form is confounded with the injected condition while its continuous form
anti-predicts. The practical implication contrasts directly with the trained-meta-learner approaches
this project deliberately avoids (Lahoti, Gummadi and Weikum, 2023): a secondary model may not be
necessary, because the signal is already present in quantities AutoML frameworks compute anyway and
then threshold badly.

## Limitations

- 25 datasets from one curated source, all binary, all numerically encoded. Nothing here speaks to
  categorical or multi-class data.
- One metric (AUROC), one outer split per seed, three seeds.
- The run-level bootstrap treats runs within a dataset as exchangeable when each dataset contributes
  21 correlated runs. This is a stronger violation than Study 1's, which had 9 per dataset.
- `delta_G = 0.05` and the two-sided labels are unchanged from Study 1 and remain stated design
  choices, not validated constants.
- Recalibrated thresholds are **not** proposed here. Fitting one would require its own holdout, and
  the obvious next study is exactly that: fit thresholds on Groups A and B, confirm on a fresh
  sample. Claim 2 establishes that calibration is the problem, not that it has been solved.
