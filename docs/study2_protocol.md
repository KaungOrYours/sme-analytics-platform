# Study 2 protocol — PRE-REGISTERED 2026-10-21, before any outcome observed

This document is written and frozen **before any Study 2 run executes**. It extends, and does not
alter, `docs/evaluation_protocol.md` (Study 1, frozen 2026-10-19). Study 1's design, thresholds,
results and conclusions are untouched; nothing here retro-fits anything there.

Why a second pre-registration rather than an amendment: Study 1's confirmatory capacity is spent.
Its development group set the thresholds and its final-evaluation group tested their transfer, so
neither can support a new confirmatory claim about a new diagnostic. Per Cawley and Talbot (2010),
the only way to make a fresh claim credible is a fresh, untouched holdout plus thresholds fixed in
advance. That is what this document establishes.

## 1. What Study 1 left open

Study 1's findings (see `docs/results_summary.md`) produced three specific, testable gaps:

1. **`n/p` is not the quantity its own cited anchor studied.** Peduzzi et al. (1996) measure *events
   per variable* — minority-class count divided by predictor count — not rows per variable. On
   imbalanced data the two diverge sharply. `appendicitis` has n/p = 15.1 (reads "safe") but
   EPV = 3.0 (reads "alarming"), and `appendicitis` is one of the datasets where `n/p` produced
   false negatives. This is a fidelity gap in Study 1's own operationalisation.
2. **Nothing measured in Study 1 can detect the failure mode that produced the most poor runs.**
   Duplicate corruption produced 29-39% poor runs against 8-11% for other families, via duplicated
   rows straddling a CV fold boundary. `n/p` is construct-mismatched for it (established by
   re-analysis) and `sigma_CV` has no positive discrimination anywhere. The mechanism is identified
   and unmeasured.
3. **Study 1's `sigma_CV > 0.10` matches no rule any AutoML framework actually ships.** It was an
   adaptation. EvalML has shipped **two** different high-variance rules (verified 2026-10-21, see
   Section 4), neither of which is a standard-deviation threshold. Study 1 therefore tested an
   adaptation, not a shipped artefact, which weakens its central claim about production software.
4. **The `poor` label is one-sided and structurally blind to outlier-induced failure.** Outlier
   corruption pushed `G` negative, so 0/24 development runs were labelled poor despite outliers
   causing the largest automated-vs-manual gap of any family.

## 2. Study 2 research questions (locked)

**RQ4.** Does events-per-variable (EPV), the quantity Peduzzi et al. (1996) actually studied,
discriminate poor outcomes better than Study 1's rows-per-feature `n/p` on the same runs?

**RQ5.** Does a direct measure of cross-validation fold contamination discriminate the
duplicate-induced optimism failure mode that `n/p` and `sigma_CV` both miss?

**RQ6.** Do EvalML's two *actually shipped* high-variance rules, implemented literally, show
predictive validity on this class of data — and does Study 1's negative result on `sigma_CV`
survive replacement of the adaptation by the real rules?

**RQ7.** Does separating the failure label into optimism (`G > +delta_G`) and pessimism
(`G < -delta_G`) reveal diagnostic validity that the one-sided label structurally cannot see,
particularly under outlier corruption?

## 3. Datasets — three groups, frozen

All 25 TabMini-eligible datasets (the full ethically-curated set; metadata pulled live via `pmlb`
on 2026-10-21, not asserted). All 25 are binary and 100% numerically encoded — zero object-dtype
feature columns anywhere — which independently confirms Study 1's exclusion of the
`inconsistent_categories` injector across the whole source, not just its own 7.

- **Group A — exploratory (7 datasets, already spent).** Study 1's development and final-evaluation
  datasets: `molecular_biology_promoters`, `appendicitis`, `biomed`, `irish`, `labor`, `mux6`,
  `bupa`. Used in Study 2 only for mechanism illustration and sanity checks. **No confirmatory
  claim may rest on Group A.**
- **Group B — development-extension (9 datasets).** Where exploratory analysis is permitted and any
  rule selection happens. `backache`, `hepatitis`, `postoperative_patient_data`,
  `analcatdata_bankruptcy`, `analcatdata_aids`, `breast_cancer`, `lupus`, `prnn_crabs`, `haberman`.
- **Group C — confirmation (9 datasets), VIRGIN.** Not to be run, inspected, or scored until the
  pre-registered analysis in Section 7 executes, once. All confirmatory claims come from Group C.
  `analcatdata_fraud`, `analcatdata_japansolvent`, `parity5`, `analcatdata_creditscore`, `glass2`,
  `corral`, `analcatdata_asbestos`, `saheart`, `prnn_synth`.

**Split rule (deterministic, no randomness):** the 18 datasets unused by Study 1, sorted by EPV
ascending with ties broken by name, assigned alternately — even index to B, odd to C. Recorded in
`evaluation/study2_dataset_split.json`. Stratified on EPV because EPV is RQ4's primary diagnostic.

Resulting balance, stated as-is rather than reshuffled to look tidier (reshuffling a split until it
looks balanced is itself a form of tuning): Group B spans EPV 0.78-27.00 with `EPV<10` firing on 6/9
and `n/p<10` on 3/9; Group C spans EPV 1.18-62.50 with `EPV<10` firing on 5/9 and `n/p<10` on 3/9.

`biomed`'s three dropped ID/metadata columns (Study 1's frozen rule) remain dropped. No other
dataset requires a column rule; this was checked across all 25 before freezing.

## 4. The diagnostics — definitions and thresholds, all fixed now

Study 1's two diagnostics (`n/p < 10`, `sigma_CV > 0.10`) are carried forward unchanged so that
Study 2's new diagnostics are compared against them on identical runs. Four new diagnostics:

| # | Diagnostic | Definition | Threshold | Anchor |
|---|---|---|---|---|
| D1 | `EPV` | minority-class count in the outer-training partition / post-encoding feature count p | `< 10` | Peduzzi et al. (1996) — the paper's own threshold, applied to the paper's own quantity |
| D2 | `fold_contamination` | mean over CV folds of the fraction of validation rows whose feature vector exactly matches at least one training-fold row | `> 0.10` | Stated design choice (Section 5) |
| D3 | `evalml_cov` | `abs(std(cv_scores) / mean(cv_scores))`; False if std == 0 or mean == 0 | `> 0.2` | EvalML's pre-PR-#2622 shipped rule, verbatim |
| D4 | `evalml_range` | `max(cv_scores) - min(cv_scores)` | `>= 0.5` | EvalML's current shipped rule, verbatim. `>=`, not `>`. For AUROC the objective's expected range is 1.0, so `threshold * allowed_range = 0.5 * 1.0` |

**Verification of D3 and D4 (2026-10-21).** EvalML's high-variance warning was re-read at source
rather than taken from Study 1's description of it, and Study 1's description turns out to be
incomplete. The framework has shipped two different rules:
- Before PR #2622: `_check_for_high_variance(self, pipeline, cv_mean, cv_std, threshold=0.2)`, using
  the coefficient of variation `abs(cv_scores.std() / cv_scores.mean()) > 0.2`, returning False when
  `std == 0` and when `mean == 0` (explicitly accepting false negatives to avoid divide-by-zero).
- After PR #2622: `_check_for_high_variance(self, pipeline, cv_scores, threshold=0.5)`, computing
  `allowed_range = objective.expected_range[1] - objective.expected_range[0]`, returning early if
  that is infinite, then flagging when `cv_range >= threshold * allowed_range`.

Study 1's `sigma_CV > 0.10` is neither of these. It remains a legitimate diagnostic to score, but it
cannot be described as "the rule EvalML ships," and Study 1's write-up must be corrected on that
point regardless of how Study 2 turns out. D3 and D4 are the literal rules.

## 5. Justification for D2's threshold, and a property of the data that complicates it

`fold_contamination > 0.10` is a round number fixed in advance, on the reasoning that one in ten
validation rows being an exact copy of a training row is a substantial violation of the independence
that cross-validation assumes. It is a stated design choice, in the same category as `delta_G = 0.05`,
and must be defended as such rather than presented as a validated constant.

**It was informed by input properties only, never by outcomes.** Before freezing, the natural
(pre-injection) exact-duplicate feature-row fraction was measured on all 25 clean datasets. This is a
property of the inputs, in the same category as n/p, and observing it does not compromise the
pre-registration. Results: 10 of 25 datasets contain duplicated feature rows with no injection at
all, ranging up to `corral` at 0.600 and `mux6` at 0.500, with `postoperative_patient_data` at 0.182
and `analcatdata_asbestos` at 0.145.

**This surfaces a conceptual problem that Study 2 must address rather than ignore.** `mux6` has 6
binary features, so only 64 distinct feature vectors exist, and n = 128. Duplicate rows are
arithmetically unavoidable. The same holds for `corral` (6 features). In low-dimensional discrete
data, fold contamination is an *intrinsic property of the feature space*, not a data-quality defect,
and a warning that fires on it is not detecting an error. Pre-registered consequence: D2 is scored
both on all runs and separately with a declared stratification by whether the dataset's feature space
is low-cardinality enough to force duplication (defined now as: number of distinct possible feature
vectors below 4n, computable from the inputs alone). If D2 only discriminates in the non-forced
stratum, that is the finding, and it will be reported as a scope condition on the diagnostic rather
than buried.

## 6. Two-sided failure labels (RQ7)

`delta_G = 0.05` is carried forward unchanged from Study 1. Three labels are computed per run:

```
G = S_CV,selected - S_test                  (unchanged definition)
poor_optimism  = 1[G >  +0.05]              (Study 1's label, unchanged)
poor_pessimism = 1[G <  -0.05]              (new)
poor_either    = 1[|G| > 0.05]              (new)
```

Every diagnostic is scored against all three labels. `poor_optimism` remains the primary label so
that Study 1's numbers stay directly comparable. The other two are secondary and labelled as such.
No threshold is re-derived; this is a relabelling of the same `G` values, not a new measurement.

## 7. Analysis plan, in execution order — fixed now

1. Run the full grid on **Group A and Group B only**: {clean, missing 15/35%, duplicates 15/35%,
   outliers 15/35%} x 3 seeds x {automated, manual}. Compute all six diagnostics and all three
   labels per run.
2. Score every diagnostic against every label on Group B. Report precision, recall, false-alarm
   rate and MCC with the run-level bootstrap CI from `evaluation_protocol.md` Section 9, carrying
   its stated exchangeability limitation. Group A is reported separately and never pooled with B.
3. **Only then** run Group C, once, and score it with the thresholds exactly as frozen above. No
   threshold, rule, or label definition may change between step 2 and step 3. If step 2 suggests a
   better threshold, that observation is reported as a suggestion for future work and the frozen
   threshold is still what step 3 uses.
4. Report MCC = 0 for degenerate confusion matrices, per Study 1 Section 6, and state every
   instance.

## 8. Pre-registered predictions

Stated so that a null result is interpretable rather than merely disappointing. Each is a directional
hypothesis that Group C can refute.

- **P1 (RQ4).** `EPV < 10` achieves a higher MCC than `n/p < 10` against `poor_optimism` on Group C.
  Mechanism: EPV accounts for the minority-class count that actually limits estimation on imbalanced
  small data. On the full 25-dataset manifest the two rules already disagree on 6 datasets, so they
  are genuinely different predictors and not a relabelling.
- **P2 (RQ5).** `fold_contamination > 0.10` achieves a positive MCC against `poor_optimism` under
  duplicate corruption on Group C, and a higher MCC than both `n/p` and `sigma_CV` in that condition.
- **P3 (RQ6).** `evalml_range >= 0.5` fires on close to no runs, because a 0.5 AUROC spread across
  folds is extreme. If so, the shipped warning is effectively inert on small tabular data — a
  stronger and more specific claim than Study 1's, and a claim about real software rather than an
  adaptation of it. `evalml_cov > 0.2` is expected to fire more often than `evalml_range` but is not
  predicted to achieve positive discrimination, consistent with Study 1's result on `sigma_CV`.
- **P4 (RQ7).** Under outlier corruption, `poor_pessimism` has a materially higher base rate than
  `poor_optimism`, and at least one diagnostic achieves positive MCC against `poor_pessimism` in a
  condition where every diagnostic was degenerate against `poor_optimism` in Study 1.

## 9. What would make Study 2 a null result, and why it would still be reportable

If none of P1-P4 hold on Group C, the reported conclusion is that cheap, deployable, untrained
diagnostics do not reliably predict automated-pipeline failure on small tabular data even when
(i) the quantity is corrected to match its literature anchor, (ii) a diagnostic is purpose-built for
the dominant observed failure mechanism, and (iii) the failure label is widened to both directions.
That is a substantive negative result about the whole class of approach, obtained under
pre-registration with an untouched holdout, and it directly motivates the trained-meta-learner
approaches (Lahoti, Gummadi and Weikum, 2023) that this project deliberately avoids. It is reported
as the answer, not reframed.

## 10. Deliberately excluded

- **No trained meta-learner.** Every diagnostic here is a closed-form function of the training
  partition and its CV scores. This preserves the distinction from Lahoti, Gummadi and Weikum (2023)
  that `docs/literature_matrix.md` draws, and keeps the diagnostics deployable at the point the
  live application would need them.
- **No diagnostic requiring the test set.** A measure that needs held-out labels cannot be a warning;
  it is a post-hoc evaluation.
- **No threshold fitted to Group B or C outcomes.** D1, D3 and D4 take their anchors' own numbers;
  D2's is a round number fixed above.
- **No new corruption family.** The three families from Study 1 are reused unchanged.

---

## Amendment 1 — 2026-10-21, after scoring Group B, BEFORE Group C was run

Group B is designated in Section 3 as the group where exploratory analysis and rule selection are
permitted, and this amendment is the result. It is dated and recorded **before Group C was executed**;
the ordering is verifiable from the results files, since `study2_group_C_results.json` did not exist
when this was written. Group C's thresholds are **not** changed by this amendment.

### A1.1 A confound in D2 that the binary threshold cannot escape

Scored on Group B, `fold_contamination > 0.10` fires on 54 of 54 duplicate-condition runs and 0 of
108 missing-value and outlier runs, plus 4 of 27 clean runs. It is therefore very nearly a detector
for "were duplicates injected," not a predictor of failure. Its apparently respectable pooled
MCC of 0.211 (CI [0.07, 0.35]) is an artifact: duplicate-condition runs have a higher poor-optimism
rate (0.574) than the other conditions (0.315 to 0.407), so any indicator of the duplicate condition
inherits discrimination it did not earn. Within the duplicates family the diagnostic is fully
degenerate, triggering on every run.

**This generalises beyond D2 and is the methodological point.** In a design where corruption is
injected, any diagnostic correlated with the injected condition will show spurious pooled
discrimination. Pooled scoring across corruption families is therefore not a safe way to evaluate
these diagnostics, and Study 1 pooled within family but never checked whether its diagnostics were
confounded with the condition. **Mandatory from here: every diagnostic is reported within corruption
family as well as pooled, and a pooled figure is never quoted without its within-family breakdown.**

### A1.2 Threshold-free AUROC added as a secondary measure

The binary thresholds are kept exactly as frozen in Section 4, and binary MCC at those thresholds
remains the primary pre-registered outcome so that P1 to P4 stay testable as written. But a binary
threshold conflates two separable questions: does the underlying quantity carry signal, and is the
threshold placed well? D2's confound is one symptom; `evalml_range` is another, and more interesting.

**Added as a declared secondary measure:** the AUROC of each diagnostic's underlying continuous value
against each failure label, computed within corruption family and pooled, with the sign oriented so
that a higher score means more predicted risk (`n/p` and `EPV` are negated, since low values are the
risk signal). This is threshold-free by construction, so it measures signal independently of
calibration. No new threshold is introduced and nothing is fitted.

### A1.3 What Group B showed, and two further predictions for Group C

Group B results (exploratory, not confirmatory — 189 runs, 78 poor-optimism, a far higher base rate
than Study 1's 8 to 11%):

- The three CV-variance diagnostics all discriminate within *every* corruption family, by AUROC:
  `sigma_cv` 0.648 / 0.731 / 0.727 / 0.753 and `evalml_cov` 0.642 / 0.711 / 0.719 / 0.789 and
  `evalml_range` 0.619 / 0.750 / 0.742 / 0.759, for clean / missing / duplicates / outliers.
- `n/p` does not (0.500 / 0.614 / 0.599 / 0.464), and its binary MCC is 0.004 with a CI spanning zero.
- `EPV` is intermediate and inconsistent (0.551 / 0.643 / 0.701 / 0.518).
- `fold_contamination` is weak once the confound is removed (0.543 / 0.514 / 0.607 / 0.629).

**This contradicts Study 1's headline negative result on `sigma_CV`**, which reported MCC CIs
excluding positive values on both of its groups. The most likely explanation is Study 1's power: 7
datasets yielding 3 poor runs per group, against 9 datasets yielding 78 here. Study 1's conclusion
must be reported as not replicating, and Study 2's Group C is the test of which result holds.

Two additional pre-registered predictions, fixed now:

- **P5.** On Group C, `sigma_cv`, `evalml_cov` and `evalml_range` each achieve AUROC > 0.6 against
  `poor_optimism` within every non-degenerate corruption family, while `n/p` and
  `fold_contamination` do not.
- **P6 (the calibration claim).** On Group C, `evalml_range` ranks among the strongest diagnostics by
  threshold-free AUROC while firing at its shipped threshold (>= 0.5) on fewer than 10% of runs. If
  both halves hold, the finding is that EvalML's shipped high-variance check measures the right
  quantity and sets its threshold far too high for small tabular data — a specific, actionable claim
  about production software, and a materially different claim from Study 1's "the warning has no
  predictive validity."

### A1.4 Unchanged by this amendment

Thresholds, labels, `delta_G`, the dataset split, the scoring scope (automated runs only), the
bootstrap procedures, and P1 to P4. Group C remains sealed until the Section 7 step 3 run.
