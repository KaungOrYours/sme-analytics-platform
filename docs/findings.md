# Consolidated findings — the project's final position

**Status: this is the authoritative statement of what the evaluation found.** Written 2026-10-22 to
reconcile three studies that, read in isolation, appear to contradict each other. Where this document
and any of `docs/results_summary.md` (Study 1), `docs/study2_results.md` or `docs/study3_results.md`
disagree, **this document is correct** — those three are the primary records of what each study
measured, and each remains accurate about its own runs, but two of them state conclusions that later
work overturned.

Nothing here is a new measurement. Every number is from a study already run, and all three studies
are reproducible from the scripts named in their protocols.

---

## 1. The headline answer

*The answer to give when someone asks what this project found, in one paragraph.*

Automated machine-learning tools ship built-in reliability warnings whose predictive validity has
never been tested. Testing them across 525 runs on 25 small tabular datasets, plus 168 further
runs on 8 datasets outside that size regime, under pre-registered protocols with untouched holdout
groups, gives a two-part answer. **The warnings
measure something real**: the cross-validation-variance signals underlying them rank runs by how
badly the pipeline is about to disappoint, with AUROC between 0.69 and 0.86, consistently, inside
every corruption type tested and on two disjoint dataset groups. **But that signal cannot be turned
into a fixed threshold that works anywhere else.** The threshold a vendor ships discards the signal
almost entirely; a threshold taken from the literature does little better; and a threshold fitted
optimally on 24 datasets performs *worse* on the 25th than the published value it replaced, because
the best cut moves by up to an order of magnitude depending on which datasets you happen to have.
These diagnostics are therefore useful as relative rankings and unreliable as absolute warnings —
which is a negative result about an entire class of cheap, deployable reliability warning, and an
argument that something adapting per dataset is required after all.

## 2. Final position on each research question

| Question | Final answer |
|---|---|
| **RQ1** — how does the automated pipeline compare with a prespecified manual baseline? | Context, not contribution. Differences are small and sample-fragile under missing values and duplicates: including one leakage-saturated dataset flips the development-group sign (+0.0172 with `irish`, −0.0240 without) while the loss count stays at 18 of 27 either way. The one robust result is under outlier corruption, where the automated pipeline wins by +0.107 to +0.169 — and that is Random Forest's known outlier robustness versus logistic regression on standardised features, not a property of automation. |
| **RQ2** — do the diagnostics discriminate the pipeline's own failures? | **Yes, as rankings.** Threshold-free AUROC 0.69–0.86 within every corruption family, on Study 2's untouched confirmation group, replicated on its exploratory group. Study 1's conclusion that `sigma_CV` had no positive discriminative value **does not replicate and is withdrawn** — see §4. |
| **RQ3** — does that discrimination transfer? | **The signal transfers; the decision rule does not.** Rankings hold on a disjoint 9-dataset group and again on 8 datasets outside the n ≤ 500 regime. Binary performance at any fixed threshold does not: it collapses toward zero on transfer and recalibration makes it worse. |
| **Does recalibration fix it?** | **No, and this is the sharpest result.** Thresholds fitted by leave-one-dataset-out generalise worse than published anchors in three of six cases (`evalml_range` 0.104 → −0.057; `sigma_cv` 0.184 → 0.043; `evalml_cov` 0.232 → 0.158) and gain nothing in the rest. The MCC-maximising threshold is itself sample-dependent: `evalml_cov`'s optimum ranges across [0.016, 0.410] over the 25 folds. |

## 3. The two contributions, in final form

**Contribution 1 — the signals are real.** Low-overhead cross-validation-variance diagnostics carry
genuine predictive information about validation-to-test optimism on small tabular data. Established
on an untouched pre-registered holdout, replicated across two disjoint dataset groups and a third
population with twice the sample size and a quarter the failure rate. This *corrects* an earlier
negative finding of this project rather than merely extending it.

**Contribution 2 — the signals are not thresholdable.** That information cannot be converted into a
fixed global cut that generalises. Demonstrated three independent ways: a shipped vendor threshold
that discards its own signal (EvalML's high-variance check carries AUROC 0.694 while firing on 6.3%
and 15.9% of runs in two groups, MCC interval crossing zero); two diagnostics with statistically
indistinguishable signal whose binary performance differs fourfold purely by where the cut sits
(`n/p` and `EPV`, AUROC 0.742 against 0.741, MCC 0.540 against 0.141); and optimally-fitted
thresholds generalising worse than the anchors they replaced.

The practical consequence, stated as the pre-registration committed to: this **partially vindicates
the trained per-instance estimators the project positioned itself against** (Lahoti, Gummadi and
Weikum, 2023). If no fixed cut generalises, something that adapts per dataset — a learned estimator,
or calibration relative to a dataset's own distribution — is the remaining option. That is a more
defensible finding than displacing that literature would have been.

## 4. The correction sequence, and why it is a strength

Two conclusions were overturned by this project's own later work. Both corrections are traceable to a
dated pre-registration written *before* the data that overturned them existed, which is what
distinguishes a correction from drift. Present it in this order; it is more defensible than
presenting only the final answer.

**Correction 1 (Study 1 → Study 2): `sigma_CV` does discriminate.**
Study 1 reported MCC intervals excluding positive values on both its groups ([−0.25, 0.00] and
[−0.26, 0.00]) and concluded the diagnostic provided no positive discrimination. Study 2 measured
+0.180 [0.04, 0.32] and +0.262 [0.12, 0.40]. The cause is statistical power: Study 1 had **3
poor-labelled runs per group**; Study 2 had 78 and 42. A diagnostic cannot be shown to discriminate
against three positive cases. Study 1's numbers are correct; the inference drawn from them was
over-confident. **This is the project's own worked example of why a low-powered evaluation produces
confident-looking wrong conclusions** — which is the same critique the project levels at published
single-benchmark validations, now evidenced from the inside.

**Correction 2 (Study 2 → Study 3): the problem is not calibration.**
Study 2 concluded the diagnostics' weakness was threshold calibration rather than construct, and
stopped short of recalibrating. Study 3 pre-registered what would falsify that claim and then
observed it: fitted thresholds generalise worse than published ones. **Study 2's Claim 2 as written
is withdrawn** and replaced by the stronger statement in §3 — not "the thresholds are mis-set" but
"no fixed threshold is a property of the diagnostic at all."

**Four of six pre-registered predictions in Study 2 were refuted or only partially supported**,
including both diagnostics purpose-built for it. One prediction was confirmed with its direction
called in advance: that `n/p`'s apparently strong +0.540 on a single group would shrink under
leave-one-dataset-out, which it did, to 0.246.

## 5. Findings that stand unchanged

These were not touched by either correction and remain as their original study reported them.

- **The `irish` leakage case study.** `Educational_level` perfectly determines the target across all
  500 rows, zero exceptions. Random Forest exploits the non-monotonic partition completely
  (AUROC 1.0, every seed); logistic regression, being linear, reaches only 0.82–0.90. The leak
  survives 35% missing-value corruption untouched. **Model selection by cross-validated score
  actively prefers the leak-exploiting model** — the pipeline's own objective is the failure
  mechanism. Both formally scored diagnostics are blind to it by construction: at saturation
  `sigma_CV` and `G` are both exactly 0. The app's own excluded leakage warning (CV ceiling 0.98)
  would have fired. **Lead the discussion chapter with this**; it is the whole thesis in one dataset.
- **Duplicate corruption is a construct-validity mismatch for `n/p`.** The hypothesis that
  duplication-inflated `n` crosses the `<10` threshold was tested across all 42 duplicate-condition
  runs and **rejected** — zero trigger disagreements. The real pattern: all 10 false negatives occur
  in datasets whose `n/p` already sits above the threshold, `bupa` worst at 100% poor across its six
  runs. More rows cannot protect against a data-integrity failure.
- **The one-sided failure label is blind to outlier-induced instability.** Outliers push `G`
  negative (cross-validation becomes pessimistic, not optimistic), so 0 of 24 development runs were
  labelled poor despite outliers causing the largest automated-versus-manual gap of any family. A
  scope limitation of the frozen measure, not a defect.
- **Sample size drives the failure mode the diagnostics target.** Halving the training partition,
  everything else held constant, multiplies the poor-outcome rate roughly sevenfold (4.8% → 33.3%).
  Independently reproduced in Study 3: the 8 datasets at n = 512–973 show a 5.4% poor rate against
  22.2% and 41.3% at n ≤ 500.
- **`n/p` is unstable across dataset samples.** +0.29, +0.50, −0.322, −0.004, +0.540 across five
  independently scored groups, and 0.246 under leave-one-dataset-out. Same rule, same threshold.

## 6. Methodological findings

Worth reporting in their own right; two came from catching mistakes rather than from a hypothesis.

- **Pooled scoring across injected corruption conditions is confounded.** A diagnostic correlated
  with the injected condition inherits discrimination it did not earn. The project's own
  `fold_contamination` scored a respectable pooled MCC of 0.211 while firing on 54 of 54 duplicate
  runs and 0 of 108 others — a detector for the *condition*, not the failure. Every figure must be
  reported within corruption family as well as pooled.
- **Low-powered evaluation yields confident wrong answers** — see Correction 1.
- **The in-regime dataset sample is exhausted.** Verified by enumerating all 162 PMLB classification
  datasets: no binary dataset with n ≤ 500 exists outside the 44 PMLBmini candidates. Any further
  confirmatory study needs a different source or a different regime.

## 7. Consolidated limitations

- 25 datasets from one curated source, all binary, all numerically encoded. Nothing here speaks to
  categorical features, multi-class targets, or large n. Inconsistent-category corruption could not
  be tested at all on this source.
- The transfer population rests on 9 poor-labelled runs; its conclusions are directional, not
  confident.
- `delta_G = 0.05` is a stated design choice, not a validated constant, and everything downstream
  inherits it. The failure label is one-sided by construction.
- Bootstrap intervals resample runs as exchangeable when each dataset contributes 9 (Study 1) or 21
  (Study 2) correlated runs. Study 3's intervals additionally understate uncertainty in the fitted
  threshold itself.
- The "automated pipeline" is three scikit-learn models at defaults with no hyperparameter search.
  **EvalML's rules were tested; EvalML was not.** Do not overclaim this.
- The SME framing motivates the *regime* — small, messy, low-n business data — not the findings. No
  SME data was used and no user testing was performed (deliberately out of scope on UH ethics
  grounds). Say this before an examiner finds it.

## 8. The obvious next study, deliberately not run

Relative or within-dataset calibration: flag the worst-ranking fraction of runs *for a given
dataset* rather than applying an absolute cut. Contribution 2 establishes that absolute thresholds
fail; it does **not** establish that no deployable rule exists, and the ranking signal is strong
enough that a relative rule is the natural candidate. It would need its own pre-registration and a
fresh population, which per §6 no longer exists in-regime.

## 9. Where each study's record lives

| Document | Still accurate about | Superseded on |
|---|---|---|
| `docs/evaluation_protocol.md` | Study 1's frozen design, thresholds, addenda | — (design, not conclusions) |
| `docs/results_summary.md` | Study 1's RQ1 results, the `irish` case, the duplicates re-analysis, Experiments 2–4 | Its `sigma_CV` conclusion (Correction 1) and its "`n/p` transfers" framing |
| `docs/study2_protocol.md` | Study 2's pre-registration and Amendment 1 | — |
| `docs/study2_results.md` | Study 2's measurements, the `fold_contamination` refutation, the power diagnosis | Its Claim 2 (Correction 2) |
| `docs/study3_protocol.md` | Study 3's pre-registration, incl. the falsification criterion | — |
| `docs/study3_results.md` | All of it; this is the most current record | — |
