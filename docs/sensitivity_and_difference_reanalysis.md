# Sensitivity and paired-difference re-analysis — closing review-response open items 1 and 2

**Written 2026-10-27. POST-HOC. Not pre-registered.**

This closes open items 1 and 2 of `docs/review_response_2026-10-22.md`, both raised by the same
22 October external critical review that produced the stratified re-analysis. Both are re-analyses
of run records already collected under the Study 2 and Study 3 protocols — **no new pipeline runs**.
Code: `evaluation/score_delta_sensitivity.py` and `evaluation/score_diagnostic_differences.py`.
Outputs: `evaluation/results/delta_g_sensitivity_scores.json`,
`evaluation/results/diagnostic_difference_scores.json`.

Scope for both: Study 2 Groups B and C, and the Study 3 transfer sample — the three sources behind
the project's current Contribution 1/2 figures in `docs/findings.md`. Group A (Study 1's spent 7
datasets) is excluded for the same reason `score_stratified.py all` excludes it.

---

## 1. `delta_G` sensitivity (open item 1)

**Purpose, stated before running, per the reviewer's own qualifier (row 10 of the disposition
table): sensitivity-only.** `delta_G = 0.05` is a round number fixed before the full-protocol
results existed (`evaluation_protocol.md` Section 4), informed only by the pilot's ~11% poor-rate
at that cutoff. It is a convenience threshold, not a validated boundary. This section asks whether
the project's headline conclusions move if that single number is varied — not whether 0.05 is the
"right" value, and it does not replace the frozen label anywhere else in the project.

**Method.** Grid of five round-number deltas chosen before looking at any result in this section,
bracketing the anchor by roughly half, 1.5x, 2x and 3x: **0.025, 0.05 (anchor), 0.075, 0.10, 0.15**.
For each delta, `poor_optimism` is recomputed directly from each run's already-collected raw `G`
(no new pipeline runs), and two already-published analyses are rescaled against the five labels:
Study 2's fixed-threshold confusion-matrix MCC (`score_study2.py`'s method) and the post-hoc
stratified concordance (`score_stratified.py`'s method, pooled and within-dataset).

**Result 1 — the poor rate moves as expected, roughly halving from the loosest to the tightest
delta:**

| Source | 0.025 | 0.05 (anchor) | 0.075 | 0.10 | 0.15 |
|---|---|---|---|---|---|
| Study 2 Group B | 92/189 (48.7%) | 78/189 (41.3%) | 70/189 (37.0%) | 61/189 (32.3%) | 48/189 (25.4%) |
| Study 2 Group C | 47/189 (24.9%) | 42/189 (22.2%) | 31/189 (16.4%) | 30/189 (15.9%) | 21/189 (11.1%) |
| Study 3 transfer | 12/168 (7.1%) | 9/168 (5.4%) | 6/168 (3.6%) | 5/168 (3.0%) | 4/168 (2.4%) |

**Result 2 — the granularity finding (Contribution 1) is unchanged at every delta tested.** On both
Group B and Group C, pooled concordance stays in a narrow band (B: 0.49–0.77; C: 0.49–0.77) while
within-dataset concordance stays consistently at or below chance (B: 0.33–0.45; C: 0.17–0.32) across
the whole grid — the gap between them never closes, let alone reverses, at any of the five deltas.
`n/p`'s pattern (near-zero-to-negative on Group B, strongly positive on Group C) also persists at
every delta — the known instability across dataset samples is a property of the samples, not of
`delta_G = 0.05` specifically.

**Result 3 — no fixed-threshold MCC changes sign across the grid**, for any of the six diagnostics,
on either Group B or Group C. Point estimates move (e.g. Group C's `n_over_p` MCC ranges 0.39–0.54,
`evalml_cov`'s ranges 0.20–0.36), but the qualitative story — `sigma_cv`/`evalml_cov`/`evalml_range`
mildly positive on both groups, `n_over_p` near-null on B and strongly positive on C — is the same
story at every tested delta.

**Result 4 — on the transfer sample, the "no fixed threshold transfers" finding is robust, and the
single-dataset fragility gets worse, not better, as the label tightens.** `evalml_range` and
`n_over_p`'s fixed-threshold MCC is exactly 0.000 at every delta in the grid (degenerate confusion
matrix); `fold_contamination`'s modest positive MCC (0.08–0.24, consistent with its known
corruption-family confound) persists at every delta too. The number of poor-labelled transfer runs
falls from 12 to 4 across the grid, which is also the number of datasets the signal can possibly be
attributed to — within-dataset concordance's bootstrap CI is already degenerate (a single valid
resample, e.g. `[0.167, 0.167]`) at the anchor and stays that way or worse at every stricter delta,
confirming the "all 9 positives come from `profb`" fragility reported in `stratified_reanalysis.md`
is not an artefact of the 0.05 cutoff — tightening the label only concentrates the evidence further.

**Conclusion.** The headline pattern is not an artefact of the specific `delta_G = 0.05` anchor. This
is a confirmatory result in the same sense Study 4 was: the project tried to show its conclusions
were contingent on an arbitrary design choice, and they were not, across a 6x range.

## 2. Paired differences between diagnostics (open item 2)

**Purpose.** `score_stratified.py` reports a separate dataset-clustered-bootstrap interval per
diagnostic. Two separately-computed intervals that overlap (or don't) are a known-unreliable proxy
for whether one diagnostic actually outperforms another — the reviewer's point. This section
computes the **paired** difference directly: every bootstrap resample draws one set of datasets and
evaluates both diagnostics in a pair on that same resample, then differences them, so the shared
resampling noise cancels the way it would in a paired test. Reuses `score_stratified.py`'s
extraction, concordance and dataset-clustered-bootstrap code unchanged; only the differencing is
new. All 15 pairs of the 6 continuous diagnostics, at two stratifications (pooled, within-dataset),
2000 resamples.

**Result 1 — pooled (the "which ranks datasets best" question): no pair differs on either
confirmatory group.** Zero of 15 pairwise differences exclude zero on Study 2 Group B or Group C.
This generalises, and gives a precise paired-test basis for, the existing Contribution 2 claim that
`n/p` and `EPV` are "statistically indistinguishable" — on this evidence *none* of the six diagnostics
is distinguishable from any other as a dataset-level ranker, in either independently-scored
confirmatory group. (On the transfer sample, 3 of 15 pairs do exclude zero, including `EPV` vs
`n_over_p`, +0.140 [0.03, 0.24] — but per §1 Result 4, the transfer sample's evidence is concentrated
in one dataset, so this is reported with that caveat rather than as a confident ranking.)

**Result 2 — within-dataset: `fold_contamination` separates from every other diagnostic, on both
Group B and Group C, and this is the corruption-family confound at finer grain, not new signal.**
`fold_contamination`'s within-dataset concordance (B: 0.643; C: 0.723) is significantly higher than
every other diagnostic's in both groups — e.g. versus `EPV`: +0.285 [0.13, 0.44] on B, +0.444
[0.24, 0.91] on C; versus `n_over_p`: +0.287 [0.13, 0.44] on B, +0.449 [0.24, 0.89] on C. Taken alone
this would look like a within-dataset discrimination success for a diagnostic the project otherwise
refuted. It is not read that way here: Study 2 Finding 4 already established that `fold_contamination`
fires on 54 of 54 duplicate-corruption runs and 0 of 108 others — it detects *which corruption family*
a run belongs to, not failure. Because every dataset in Groups B and C contributes runs from all four
families, that family-detection ability survives *within* a dataset exactly as well as it does
pooled, producing a within-dataset concordance that looks like signal but is the identical confound
at a finer grain. This explanation is consistent with, but not independently re-verified by, this
script — it would need the family-stratified within-dataset concordance Study 2 Finding 4 already
computed pooled, re-run within dataset, to confirm directly. Flagged as the natural next check if
`fold_contamination` is revisited.

**Result 3 — a smaller, consistent side finding: `sigma_cv` and `evalml_cov` are not interchangeable
despite both being CV-variance adaptations of EvalML's rule.** `sigma_cv`'s within-dataset
concordance exceeds `evalml_cov`'s on both confirmatory groups (+0.069 [0.03, 0.11] on B; +0.080
[0.01, 0.18] on C) — small but reproduced in both independently-scored groups. `evalml_range` also
exceeds `evalml_cov` on Group B (diff `evalml_cov` − `evalml_range` = −0.074 [−0.12, −0.03]). The two EvalML-style
operationalisations (coefficient of variation versus range) are not simply interchangeable proxies
for "high variance", even though `evaluation_protocol.md` treats them as adaptations of the same
vendor precedent.

**Result 4 — the transfer sample's within-dataset intervals are uniformly degenerate.** Every
within-dataset paired-difference CI on `study3_transfer` has `ci_low == ci_high` (one valid bootstrap
resample out of 2000) — the same single-dataset (`profb`) dependency already reported, now visible
as a property of every pairwise comparison, not only the marginal diagnostic intervals.

**Conclusion.** The paired test adds precision without changing any existing claim: no diagnostic
beats another as a dataset ranker in either confirmatory group (strengthening "the signal is a
dataset-level property shared across diagnostics, not a property of any one of them"); the one
within-dataset separation that does appear (`fold_contamination`) has a ready explanation already on
record rather than being a new discriminative success; and the EvalML-rule-variant finding is new but
narrow — worth a sentence in the discussion chapter, not a revision to either contribution.

## 3. What this does and does not establish

Both checks are **sensitivity/precision additions to existing claims, not new experiments.** Neither
changes a headline number, a contribution, or a correction. Both are post-hoc and are labelled as
such everywhere they are reported, per the project's standing convention. Open items 1 and 2 of
`docs/review_response_2026-10-22.md` are closed by this document.
