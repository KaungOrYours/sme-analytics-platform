# Response to external critical review, 22 October 2026

An independent critical reading of this project's research documents was obtained on 22 October
2026 (`AutoML_Strict_Examiner_Pushback_2026-10-22.md`, reviewing the protocols, results, findings
and draft chapters; no code was executed by the reviewer). Its verdict was "major revisions to
interpretation, inferential analysis and narrative; not a demand for a new experiment."

This document records what was done about each point. It is deliberately kept as a record rather
than folded silently into the other documents: a reviewer's objections and the project's response
to them are evidence of process, and the viva can ask about any row.

**Summary: one claim was narrowed, one was downgraded, and no measurement changed.** All 48
published figures checked were re-derived from committed code and reproduce exactly to 3 d.p. The
revisions are to what the numbers were taken to mean.

---

## Disposition against the reviewer's priority matrix

| # | Reviewer's point | Verdict | What was done |
|---|---|---|---|
| 1 | **Critical** — "cannot be converted into a fixed global threshold" asserts an impossibility not proved | **Accepted** | `findings.md` §1 and §3 rewritten to bounded language, with an explicit "what this does *not* establish" paragraph naming the untested alternatives (other diagnostics, other objectives, other populations, relative calibration). The conditional scope is stated in the headline paragraph itself, not only in limitations. |
| 2 | **Critical** — bootstrap resamples correlated runs, intervals anti-conservative | **Accepted and measured** | `evaluation/score_stratified.py` implements a dataset-clustered bootstrap (whole datasets resampled, 2000 resamples). Effect is large: Group C's headline `sigma_cv` figure goes from a run-level interval excluding chance to **0.706 [0.43, 0.88], which includes chance.** Reported in `stratified_reanalysis.md` §4 and carried into `findings.md` §2 and §7. |
| 3 | **Critical** — `irish` labelled definitive leakage without provenance | **Accepted** | Reworded to *suspected target-derived coding* in `findings.md` §5 and `datasets.md`. Checked whether provenance could be settled: PMLB ships no codebook for this dataset and none was obtained, so the question is genuinely open. The non-monotonic {0,1,10} / {2..9} partition is retained as the specific evidence, with the inference marked pending. Reading the original source codebook is now a named open action. |
| 4 | **High** — `sigma_CV` and `G` share CV scores; discrimination may be mechanical | **Accepted, and it cuts the other way** | Tested directly by stratification. A mechanical coupling would appear *within* dataset; within-dataset concordance is at or below chance, so coupling is not generating the positive pooled signal. Recorded in `stratified_reanalysis.md` §6. The within-dataset *reversal* is reported as an open observation with shared-fold noise named as an untested candidate mechanism — not explained away. |
| 5 | **High** — transfer rests on 9 positives; report per-dataset counts | **Accepted; worse than the reviewer knew** | Per-dataset × family outcome counts with NA flags are now emitted by the scorer. **All 9 positive cases come from one dataset (`profb`); the other 7 have none.** Only 2 of 32 cells are estimable, and 36% of cluster resamples contain no positive at all, so the transfer intervals are conditional on drawing that dataset. Study 3's RQ9 conclusion is downgraded in its banner and in `findings.md` §2. |
| 6 | **High** — pooled results confounded by dataset and corruption; separate between- from within-dataset | **Accepted — this became the session's main finding** | Full decomposition in `stratified_reanalysis.md`: pooled / within-family / within-dataset / within dataset×family / within dataset×family×rate. Confirms the reviewer's specific prediction about `n/p` (3.0 distinct values per dataset, 2.3% within-dataset variance, exactly 0.500 at the strictest stratification) **and extends it to every CV-variance diagnostic.** Contribution 1 narrowed accordingly. The "which product is this?" question is answered explicitly: it is a dataset-risk indicator, not a run-risk indicator. |
| 7 | **High** — sequential studies need a provenance audit; dated headers are not proof | **Accepted** | Audit table added as `findings.md` §8, including the uncomfortable part: **Studies 2 and 3 committed protocol and results in the same commit (`1acb3f9`, `154fb3a`), so git does not prove the freeze.** Supporting evidence named (the `--confirm` gate on Group C; Amendment 1 recorded before C ran). Cannot be fixed retroactively; future studies commit the protocol first. |
| 8 | **High** — vendor claims broader than implementation | **Accepted** | `findings.md` §7 states "EvalML's warning *rules* were reimplemented and tested; EvalML itself was never run", and §1 constrains the headline to three scikit-learn models at defaults. To be repeated in the abstract and conclusion when written. |
| 9 | **High** — chapters 3 and 5 unsafe to submit | **Accepted** | Both already carried banners; both extended with the specific constraints the rewrite must satisfy (within-dataset columns beside every pooled figure, clustered intervals, the single-dataset transfer caveat, the new methodology sections). The outline's Ch6 note, which still led with Study 1's withdrawn conclusion, was rewritten. |
| 10 | **Moderate** — `delta_G = 0.05` is a convenience, not a truth oracle; "the pipeline's own failures" overruns it | **Accepted** | `findings.md` §7 now says the label records "observed validation-to-test optimism on one noisy held-out score", not failure in any broader sense. The sensitivity analysis over alternative deltas the reviewer suggests is **not done** — see open items. |
| 11 | **Moderate** — RQ1 confounds automation with model class | **Accepted** | `findings.md` §2 RQ1 row and §7 now state that no RQ1 figure isolates automation from model family, and that the outlier result is Random Forest versus logistic regression. |
| 12 | **Moderate** — coverage, representativeness, "first-ever" wording | **Accepted** | §7 bounds external validity (one curated source, binary only, numerically encoded, transfer sample partly synthetic Boolean tasks) and replaces universal wording: "the reviewed studies did not establish this", never "first ever". Licence/ethics screening is still recorded as inherited from TabMini's curation and not independently verified — unchanged, and already flagged as an open item. |
| 13 | **Moderate** — the size effect is not causally established across benchmarks | **Accepted** | `findings.md` §5 now presents the controlled within-dataset halving as the evidence and explicitly labels the cross-benchmark 5.4%-vs-22/41% contrast as consistent but **not** independent confirmation. The phrase "independently reproduced" was removed. |

## Points where the project's existing record was better than the review credited

Recorded for fairness, not to dismiss the review — the reviewer could not run anything and these
were visible only in files they weighted differently.

- The corruption-family confound (reviewer §6's first half) had already been found by this project,
  named as Study 2 Finding 5, and acted on: every figure since is reported within family. What was
  missed was the *dataset* version of the same argument.
- Outlier-family degeneracy in transfer (reviewer §5) is stated explicitly in `study3_results.md`
  with its mechanism. The overclaim was in `findings.md`'s headline, not in the study record.
- Refuted predictions were already retained visibly, including both diagnostics the project built
  for itself.
- `delta_G`'s pilot-informed, deliberately diagnostic-independent selection was already documented
  in `evaluation_protocol.md`.

## Open items this review raises that are NOT closed

1. **Sensitivity analysis over alternative `delta_G`** (reviewer §9). Not run. Would be
   straightforward re-analysis of existing runs; should be pre-declared as sensitivity-only and
   must not replace the headline label.
2. **Uncertainty on *differences* between diagnostics** on common held-out datasets (reviewer §2),
   rather than separate intervals per diagnostic. Not computed.
3. **`irish` codebook.** Needs the original source document to settle leakage versus legitimate
   covariate. Student action.
4. **Module FPR brief** — word budget and citation style still assumed, not verified. Student
   action, and it blocks nothing until the chapters are written.
5. **Per-dataset original licence text** and **UH formal ethics confirmation** — unchanged from the
   outline's existing open items 2 and 3.
6. **The within-dataset reversal** (concordance below 0.5) has a named candidate mechanism and no
   test. Deserves its own pre-registration.

## What the reviewer got wrong

Little, but one thing matters for the write-up. The review treats the ranking-versus-threshold
distinction as the project's strongest surviving contribution and frames the granularity issue
(§6) as a reporting request. It is the reverse: once the granularity decomposition is run, it
*subsumes* the threshold finding — a dataset-level signal cannot support a global run-level cut,
so the threshold failures are a consequence rather than a separate result. The report should lead
with granularity and derive thresholds from it.
