# Consolidated findings — the project's final position

**Status: this is the authoritative statement of what the evaluation found.** Written 2026-10-22 to
reconcile three studies that, read in isolation, appear to contradict each other; **substantially
revised later the same day** after a post-hoc stratified re-analysis
(`docs/stratified_reanalysis.md`) showed the first of the two headline claims was measuring
something narrower than it said. Where this document and any of `docs/results_summary.md`
(Study 1), `docs/study2_results.md` or `docs/study3_results.md` disagree, **this document is
correct** — those three remain accurate about their own measurements, but three of their stated
conclusions were overturned by this project's own later work.

Nothing here is a new measurement. Every number is from a study already run, and all are
reproducible from the scripts named in their protocols.

---

## 1. The headline answer

*The answer to give when someone asks what this project found, in one paragraph.*

Automated machine-learning tools ship built-in reliability warnings whose predictive validity has
never, as far as the reviewed literature shows, been empirically tested. Testing them across 525
runs on 25 small binary tabular datasets, plus 168 further runs on 8 datasets outside that size
regime, under pre-registered protocols with an untouched holdout group, gives a two-part answer.
(A fourth study re-measured those same 525 runs under more precise variance estimators; it added no
new pipeline runs and no new datasets, so the project's totals remain 861 runs over 33 datasets.)
**The warnings measure something real, but coarser than they claim to**: the cross-validation-variance
signals underlying them rank *datasets* by how likely the pipeline is to be over-optimistic
(between-dataset Spearman rho +0.88 to +0.94), and carry essentially no ability to tell which
*individual run* within a dataset will disappoint (within-dataset concordance 0.14–0.44 across the
three samples, intervals at or below chance). That per-run null is not an artefact of a crude
estimator: re-measuring the same 525 runs with the cross-validation repeated ten and twenty times
left it flat to declining (0.332, 0.301, 0.265), and the residual within-dataset association runs
*backwards* for a mechanical reason — AUROC is capped at 1, so a high cross-validation mean forces
low fold variance while raising the optimism outcome by construction. **And that signal cannot be
converted into a fixed threshold that transfers**: the
threshold a vendor ships discards it almost entirely, thresholds taken from the literature reach
MCC 0.10–0.24 at best, and a threshold fitted optimally by leave-one-dataset-out performs *worse* on
the held-out dataset than the published value it replaced, because the best cut moves by up to an
order of magnitude depending on which datasets you happen to hold. The second result follows from
the first: if the signal is a property of the dataset, a global cut on a run-level quantity has
nothing stable to cut on. These diagnostics are usable as a coarse relative ranking of datasets and
unreliable as absolute per-run warnings.

**Everything above is conditional on**: this benchmark family, binary targets only, the four
corruption conditions tested, the `delta_G = 0.05` optimism label, three scikit-learn model families
at default hyperparameters, and 8–9 independent datasets per group. It does not establish that no
fixed threshold can work, nor that trained meta-models are required.

## 2. Final position on each research question

| Question | Final answer |
|---|---|
| **RQ1** — how does the automated pipeline compare with a prespecified manual baseline? | Context, not contribution. Differences are small and sample-fragile under missing values and duplicates: including one saturated dataset flips the development-group sign (+0.0172 with `irish`, −0.0240 without) while the loss count stays at 18 of 27 either way. The one robust result is under outlier corruption, +0.107 to +0.169 — and that is **Random Forest's outlier robustness versus logistic regression on standardised features, not an effect of automation.** No RQ1 figure isolates automation from model class. |
| **RQ2** — do the diagnostics discriminate the pipeline's own failures? | **Partly, and at the wrong granularity.** They discriminate *between datasets* (pooled concordance 0.64–0.71, within-family 0.73–0.89) but not *within* one (0.14–0.44, intervals at or below 0.5; `n/p` is literally constant within a dataset). Under a dataset-clustered bootstrap even the pooled Group C figure, 0.706 [0.43, 0.88], includes chance. Study 1's conclusion that `sigma_CV` had *no* discriminative value does not replicate and is withdrawn — see §4. |
| **RQ3** — does that discrimination transfer? | **Not demonstrated.** The 8-dataset transfer sample contains 9 poor-labelled runs and **all 9 come from one dataset** (`profb`); 36% of cluster-bootstrap resamples contain no positive case at all. What transferred is that one dataset of eight was correctly ranked riskiest. Binary performance at any fixed threshold does not transfer: it collapses toward zero. |
| **Does recalibration fix it?** | **No, and this is the sharpest surviving result.** Thresholds fitted by leave-one-dataset-out generalise worse than published anchors in three of six cases (`evalml_range` 0.104 → −0.057; `sigma_cv` 0.184 → 0.043; `evalml_cov` 0.232 → 0.158) and gain nothing in the rest. The MCC-maximising threshold is itself sample-dependent: `evalml_cov`'s optimum ranges across [0.016, 0.409] over the 25 folds. |

## 3. The two contributions, in final form

**Contribution 1 — the signals are real, but they are dataset-level, not run-level.** Low-overhead
cross-validation-variance diagnostics rank datasets by their propensity to produce
validation-to-test optimism (Spearman rho +0.88 to +0.94 across two independent 9-dataset groups),
while carrying no usable within-dataset discrimination. This distinction is not drawn in the
literature these rules come from, and it matters commercially: a warning attached to a single
pipeline run is sold as a per-run signal and is being computed from a dataset-level property.
Established on pre-registered holdout measurements; the between/within decomposition itself is
post-hoc (`docs/stratified_reanalysis.md`). **Study 4 tested and eliminated the obvious objection to
it**: the per-run null is not an artefact of estimating a standard deviation from five fold scores.
Repeating the cross-validation ten and twenty times, which cut the diagnostic's within-dataset
variance share from 0.399 to 0.238 and moved per-run values by about 30 per cent of their own
magnitude, left within-dataset concordance at 0.332, 0.301 and 0.265 — flat to declining, every
interval below chance (`docs/study4_results.md`).

**Contribution 2 — the signals are not thresholdable, and Contribution 1 explains why.** The
information cannot be converted into a fixed global cut that generalises across dataset samples.
Demonstrated three ways: a shipped vendor threshold that discards its own signal (EvalML's
high-variance check carries pooled concordance 0.694 while firing on 6.3% and 15.9% of runs, MCC
interval crossing zero); two diagnostics with statistically indistinguishable signal whose binary
performance differs fourfold purely by where the cut sits (`n/p` and `EPV`, 0.742 against 0.741
pooled, MCC 0.540 against 0.141); and optimally-fitted thresholds generalising worse than the
anchors they replaced. If the signal is a dataset-level property, a global cut on a run-level
quantity has nothing stable to cut on — so the second contribution is the predicted consequence of
the first, not an independent surprise.

**What this does *not* establish.** That no fixed threshold can work for any diagnostic, objective
or population; only MCC-maximising calibration on this benchmark was tested. That trained
per-instance estimators (Lahoti, Gummadi and Weikum, 2023) are *necessary* — that remains a
hypothesis. The pre-registration committed to reporting that these results point back toward
adaptive approaches, and they do, but as a direction for future work rather than a demonstrated
requirement.

## 4. The correction sequence, and why it is a strength

Three conclusions were overturned by this project's own later work. Present them in this order; it
is more defensible than presenting only the final answer. **Study 4 is deliberately not on this list:
it tested a fourth possible correction, pre-registered what would constitute one, and found none.
That is a confirmation, and it should be presented as the sequence's one case where the project tried
to break its own claim and failed.**

**Correction 1 (Study 1 → Study 2): `sigma_CV` does discriminate.**
Study 1 reported MCC intervals excluding positive values on both groups ([−0.25, 0.00] and
[−0.25, 0.00]) and concluded the diagnostic had no positive discrimination. Study 2 measured +0.180
[0.04, 0.32] and +0.262 [0.12, 0.40]. The cause is statistical power: Study 1 had **3 poor-labelled
runs per group**; Study 2 had 78 and 42. A diagnostic cannot be shown to discriminate against three
positive cases. Study 1's numbers are correct; the inference was over-confident. **This is the
project's own worked example of why a low-powered evaluation produces confident-looking wrong
conclusions** — the same critique the project levels at published single-benchmark validations, now
evidenced from the inside.

**Correction 2 (Study 2 → Study 3): the problem is not calibration.**
Study 2 concluded the weakness was threshold calibration rather than construct, and stopped short of
recalibrating. Study 3 pre-registered what would falsify that and then observed it: fitted thresholds
generalise worse than published ones. **Study 2's Claim 2 as written is withdrawn.**

**Correction 3 (Studies 2–3 → stratified re-analysis): the discrimination is between-dataset.**
All three studies pooled runs across datasets, so their discrimination figures could not separate
"this dataset is risky" from "this run will disappoint". Stratifying shows it is almost entirely the
former, and that clustered intervals on the headline figures include chance. Unlike Corrections 1
and 2, **this one was prompted by external review and is post-hoc, not pre-registered** — that
distinction is stated wherever it is reported.

**Four of six pre-registered predictions in Study 2 were refuted or only partially supported**,
including both diagnostics purpose-built for it. One was confirmed with its direction called in
advance: that `n/p`'s apparently strong +0.540 on a single group would shrink under
leave-one-dataset-out, which it did, to 0.246.

## 5. Findings that stand unchanged

- **The `irish` saturation case study.** `Educational_level` determines `target` exactly across all
  500 rows. The mapping is **non-monotonic** — codes 0, 1 and 10 map to `target=1` (222 rows), codes
  2–9 to `target=0` (278 rows) — which is inconsistent with an ordinal attainment covariate that
  merely correlates strongly, and consistent with a code whose categories partition on the target's
  own definition. Random Forest exploits the partition completely (AUROC 1.0, every seed); logistic
  regression, being linear, reaches only 0.82–0.90. The relationship survives 35% missing-value
  corruption untouched. **Model selection by cross-validated score actively prefers the
  saturation-exploiting model** — the pipeline's own objective is the failure mechanism. Both
  formally scored diagnostics are blind to it by construction: at saturation `sigma_CV` and `G` are
  both exactly 0. The app's own excluded leakage warning (CV ceiling 0.98) would have fired.
  **Call this *suspected target-derived coding*, not proven leakage.** A perfect in-sample predictor
  is equally consistent with legitimate redundancy; distinguishing them needs the original codebook,
  which is not distributed with the PMLB copy and has not been read. The empirical result and the
  non-monotonicity are solid; the *interpretation* is pending provenance. **Lead the discussion
  chapter with this** — it is the whole thesis in one dataset.
- **Duplicate corruption is a construct-validity mismatch for `n/p`.** The hypothesis that
  duplication-inflated `n` crosses the `<10` threshold was tested across all 42 duplicate-condition
  runs and **rejected** — zero trigger disagreements. The real pattern: all 10 false negatives occur
  in datasets whose `n/p` already sits above the threshold, `bupa` worst at 100% poor across its six
  runs. More rows cannot protect against a data-integrity failure.
- **The one-sided failure label is blind to outlier-induced instability.** Outliers push `G`
  negative (cross-validation becomes pessimistic, not optimistic), so 0 of 24 development runs were
  labelled poor despite outliers causing the largest automated-versus-manual gap of any family. A
  scope limitation of the frozen measure, not a defect.
- **Smaller training sets raise the failure rate, within dataset.** Halving the training partition
  with everything else held constant multiplies the poor-outcome rate roughly sevenfold
  (4.8% → 33.3%). This is the controlled evidence. The separate observation that Study 3's
  larger-n datasets show 5.4% poor against 22.2% and 41.3% is **consistent with it but not
  independent confirmation** — those are different datasets differing in difficulty, feature
  structure and labels, not only in `n`.
- **`n/p` is unstable across dataset samples.** +0.29, +0.50, −0.322, −0.004, +0.540 across five
  independently scored groups, and 0.246 under leave-one-dataset-out. Same rule, same threshold.
- **The sub-chance within-dataset concordance is a bounded-metric confound, and the two earlier
  candidate explanations are refuted.** Within-dataset concordance sits consistently *below* 0.5, not
  merely at it. Study 4 eliminated estimator imprecision (Section 3 above) and eliminated shared fold
  noise by computing `sigma` and `G` from disjoint sets of repeats, which left the figure unchanged at
  0.265 [0.18, 0.36]. The supported explanation is post-hoc and mechanical: AUROC is bounded at 1, so
  within one dataset a run whose CV mean lands near the ceiling is forced toward low fold variance
  while the same high mean raises `G = S_CV − S_test` by construction. Measured within dataset, median
  over 25 datasets: CV mean against `sigma` −0.813 (24 of 25 negative), CV mean against `G` +0.688
  (25 of 25 positive), `sigma` against `G` −0.630 raw but **−0.075 once the CV mean is partialled
  out**. Twenty per cent of runs have a CV mean above 0.95. See `docs/study4_results.md` section 6;
  that section is post-hoc.

## 6. Methodological findings

Worth reporting in their own right; three came from catching mistakes rather than from a hypothesis.

- **Pooled scoring across injected corruption conditions is confounded.** A diagnostic correlated
  with the injected condition inherits discrimination it did not earn. The project's own
  `fold_contamination` scored a pooled MCC of 0.211 while firing on 54 of 54 duplicate runs and 0 of
  108 others — a detector for the *condition*, not the failure.
- **Pooled scoring across datasets is confounded the same way, and this was missed for longer.**
  See Correction 3. The general lesson: *every* grouping variable that predicts the outcome must be
  stratified on, not just the one you injected yourself.
- **Run counts overstate evidence.** 525 runs are 25 datasets; 168 transfer runs are 8 datasets, of
  which exactly one contains any failure. Report estimable clusters, not row counts.
- **Low-powered evaluation yields confident wrong answers** — see Correction 1.
- **The in-regime dataset sample is exhausted.** Verified by enumerating all 162 PMLB classification
  datasets: no binary dataset with n ≤ 500 exists outside the 44 PMLBmini candidates.
- **A question about an estimator does not need fresh data.** The sample exhaustion above blocks any
  claim about generalising to new datasets, but not a claim about the estimator, because that
  comparison is within run and each run is its own control. Study 4 was possible for this reason.
- **A bounded score plus a difference-of-means outcome manufactures a confound.** With AUROC capped
  at 1 and `G` defined as `S_CV − S_test`, the CV mean pushes the variance diagnostic down and the
  outcome up simultaneously. Any per-run association between a variance diagnostic and `G` must
  control for the mean; this project's early figures did not.

## 7. Consolidated limitations

- 25 datasets from one curated source, all binary, all numerically encoded; the 8 transfer datasets
  are partly synthetic Boolean-function tasks. Nothing here speaks to categorical features,
  multi-class targets, or large n. Inconsistent-category corruption could not be tested at all.
- Effective sample size is 8–9 independent datasets per group, not 189 runs. Dataset-clustered
  intervals on the headline discrimination figures include chance.
- Studies 1–3 reported run-level bootstrap intervals, which are anti-conservative. The clustered
  intervals in `stratified_reanalysis.md` supersede them for any cross-dataset claim; the earlier
  per-run `S_test` intervals remain valid for their own narrower purpose.
- **`G`'s own construction carries a confound.** Because AUROC is bounded above and `G` is a
  difference of means, the CV mean is associated with the variance diagnostic negatively and with `G`
  positively within every dataset. This is a property of this project's chosen outcome measure, not of
  CV-variance diagnostics generally, and it bounds every per-run claim about `G`.
- `delta_G = 0.05` is a stated design choice, not a validated constant. The label records
  **observed validation-to-test optimism on one noisy held-out score** — not "the pipeline's own
  failures" in any broader sense, and it is one-sided by construction.
- The "automated pipeline" is three scikit-learn models at default hyperparameters with no search.
  **EvalML's warning *rules* were reimplemented and tested; EvalML itself was never run.** This is
  not a benchmark of any deployed AutoML platform's warnings in its native workflow.
- RQ1 compares model families as much as it compares automation. No figure isolates the effect of
  automation.
- The claim that no prior empirical evaluation of these warnings exists rests on the 7-reference
  review in `docs/literature_matrix.md`, which is not a systematic review. State it as "the reviewed
  studies did not establish this", never as "first ever".
- The SME framing motivates the *regime* — small, messy, low-n business data — not the findings. No
  SME data was used and no user testing was performed (out of scope on UH ethics grounds).

## 8. Provenance audit

What was frozen when, and what each conclusion is entitled to claim. **Honest limitation: Studies 2
and 3 had their protocol and results files committed in the same commit, so git history does not by
itself prove the protocol predated the run.** **Study 4 is the one study where it does**: `7cab9db`
contains the protocol and nothing else, and the runner and results were committed afterwards. The supporting evidence is the `--confirm` gate that
`full_run_study2.py` requires before Group C can be run, and Study 2's Amendment 1 being recorded
before Group C's results file existed. Future studies commit the protocol before running.

| Study | Protocol | Commit | Datasets already inspected | Genuinely untouched at run time | Status of its conclusions |
|---|---|---|---|---|---|
| Study 1 | `evaluation_protocol.md`, frozen 2026-10-19 after a required pilot | `cb8e3a0` (protocol), results later | 3 development datasets used in the pilot | the 3 final-evaluation datasets | RQ1 stands; `sigma_CV` conclusion **withdrawn** (power) |
| Study 2 | `study2_protocol.md`, pre-registered 2026-10-21 | `1acb3f9` (protocol **and** results together) | Study 1's 7 (Group A, declared spent) | Group C's 9, never inspected before scoring | Measurements stand; **Claim 2 withdrawn**; Claim 1 **narrowed** by Correction 3 |
| Study 2 Amendment 1 | appended to `study2_protocol.md` | same | Groups A and B scored | Group C | Added threshold-free AUROC as a declared secondary measure, recorded before Group C ran |
| Study 3 | `study3_protocol.md`, pre-registered 2026-10-21 | `154fb3a` (protocol **and** results together) | all 25 (leave-one-out is re-analysis) | the 8 transfer datasets | Recalibration result stands; transfer claim **downgraded** (1 estimable dataset) |
| Stratified re-analysis | `stratified_reanalysis.md` | 2026-10-22 | everything | nothing | **Post-hoc, externally prompted, exploratory.** Revises claims; confirms nothing |
| Study 4 | `study4_protocol.md`, pre-registered 2026-10-23 | **`7cab9db` — protocol ALONE, before the runner or any result existed** | all 25 (no holdout claimed) | nothing | Confirms Contribution 1 against its strongest objection; P11 and P14 refuted, P12 and P13 held. Its Section 6 mechanism is post-hoc |

Refuted predictions are retained in `study2_results.md` §"Status of each pre-registered prediction"
and `study3_results.md`, and are not quietly dropped.

## 9. The obvious next study, deliberately not run

Relative or within-dataset calibration: flag the worst-ranking fraction of runs *for a given
dataset* rather than applying an absolute cut. **Correction 3 weakens the case for this and Study 4
weakens it further** — the within-dataset signal survived neither a 20x more precise estimator nor
decoupling, and what residual association exists runs the wrong way for mechanical reasons.
— the within-dataset ranking signal is at or below chance, so the natural candidate rule now looks
unpromising on this project's own evidence. The better-supported next step is to test whether the
*dataset-level* signal, which is strong, can be turned into a dataset-level admission decision
("is this dataset safe to automate at all?"), which is a different and more honest product.

## 10. Where each study's record lives

| Document | Still accurate about | Superseded on |
|---|---|---|
| `docs/evaluation_protocol.md` | Study 1's frozen design, thresholds, addenda | — (design, not conclusions) |
| `docs/results_summary.md` | Study 1's RQ1 results, the `irish` case, the duplicates re-analysis, Experiments 2–4 | Its `sigma_CV` conclusion (Correction 1) and its "`n/p` transfers" framing |
| `docs/study2_protocol.md` | Study 2's pre-registration and Amendment 1 | — |
| `docs/study2_results.md` | Study 2's measurements and the `fold_contamination` refutation | Its Claim 2 (Correction 2); its pooled AUROC *interpretation* (Correction 3) |
| `docs/study3_protocol.md` | Study 3's pre-registration, incl. the falsification criterion | — |
| `docs/study3_results.md` | The recalibration result | Its RQ9 transfer conclusion (Correction 3) |
| `docs/stratified_reanalysis.md` | The between/within decomposition and clustered intervals | — |
| `docs/study4_protocol.md` | Study 4's pre-registration, provably frozen before the run | — |
| `docs/study4_results.md` | The estimator-precision test, the decoupling refutation, and the bounded-metric mechanism | — (most current) |
