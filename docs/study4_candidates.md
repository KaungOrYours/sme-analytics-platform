# Study 4 — candidate routes, and the literature behind them

**Status: a decision memo, not a protocol.** Nothing here has been run. Written 2026-10-23. Once a
route is chosen, it gets a pre-registered protocol that is **committed before any run** — Studies 2
and 3 committed protocol and results together and that cost the project its cleanest evidence of
pre-registration (`docs/findings.md` section 8). Do not repeat it.

## 1. The problem a fourth study has to solve

The project's position after the stratified re-analysis is that the cross-validation-variance
diagnostics rank *datasets* by optimism risk (between-dataset Spearman rho +0.88 to +0.94) and carry
no usable *within-dataset, per-run* discrimination (0.14 to 0.44, intervals at or below chance), and
that the second contribution follows from the first.

There is an obvious objection to that, and it has not been answered:

> `sigma_CV` is the standard deviation of **five numbers**. Of course it cannot discriminate within a
> dataset. You have not shown the signal is absent; you have shown your estimator is too crude to
> find it.

This is verified against the code, not assumed: `evaluation/diagnostics.py:64` computes
`cv_scores_for_model` with a single `StratifiedKFold(n_splits=5)`, and `sigma_cv` is
`best_scores.std(ddof=1)` over those five values. Every published figure in Studies 1 to 3 rests on
a five-sample standard deviation.

**That objection is the most dangerous one an examiner can raise, because the project has already
conceded exactly this failure mode once.** Correction 1 withdrew Study 1's "`sigma_CV` has no
discriminative value" precisely because it rested on three positive cases. A reader who has just been
walked through that correction will immediately ask whether Correction 3's within-dataset negative is
the same mistake in a new place.

A fourth study should answer that question rather than leave it for the viva.

## 2. What the literature says, and where the gap actually is

Three real, verified publications bear directly on this. **None is among the 7 locked references from
the approved plan, and none has been read by the student** — they are listed here as leads, and
nothing may be cited in the FPR until read (see `docs/literature_matrix.md`).

| Reference | What it establishes | Why it matters here |
|---|---|---|
| **Bengio, Y. and Grandvalet, Y. (2004)** 'No Unbiased Estimator of the Variance of K-Fold Cross-Validation', *JMLR*, 5, pp. 1089-1105 | There is **no universally unbiased estimator** of the variance of k-fold CV. Fold estimates are dependent because training sets overlap, and naive estimators that ignore this correlation **can grossly underestimate the variance** | The project's `sigma_CV`, and EvalML's shipped rules, *are* that naive estimator. A vendor is thresholding a quantity that has been known for twenty years to be a biased estimate of what it appears to measure |
| **Bates, S., Hastie, T. and Tibshirani, R.** 'Cross-validation: what does it estimate and how well does it do it?', *JASA*. DOI 10.1080/01621459.2023.2197686 (arXiv:2104.00673) | Cross-validation **approximates a different error than the one of interest**: it estimates the average error over the population of training sets, not the error of the particular model you fitted. Naive CV intervals can have coverage far below nominal. They propose a **nested scheme** that targets the practitioner's quantity | **This is the theoretical statement of what this project found empirically.** The project discovered by stratification that the signal is dataset-level and not fit-level; Bates et al. derive that CV targets a population-level quantity rather than a fit-level one. Same claim, two directions |
| **Varoquaux, G. (2018)** 'Cross-validation failure: small sample sizes lead to large error bars', *NeuroImage* (arXiv:1706.07581) | At small n, CV error bars are large and CV-based conclusions are unstable | Directly on this project's regime (n <= 500) and supports the sample-size mechanism already found in Experiment 4 |

**Where the gap is.** The AutoML evaluation literature found in searching is about *comparing
frameworks* — which tool wins on which benchmark, run-to-run variability across frameworks. It does
not test whether a framework's own shipped reliability warning predicts that framework's own failure.
Meanwhile the statistics literature on CV variance is mature and does not discuss shipped AutoML
warning rules at all. **Neither side has connected to the other.** That junction is the strongest
novelty position available, and it is better than the project's current framing because it supplies a
*mechanism* rather than only an observation.

Caveat, stated plainly: this is a targeted search, not a systematic review. The claim must be phrased
as "the reviewed literature does not establish this", never as "first ever" — the same bound already
applied in `docs/findings.md` section 7.

## 3. The four candidate routes

### Route A — The estimator hypothesis *(recommended)*

**Question.** Does the absence of within-dataset discrimination survive a variance estimator that is
not the naive five-fold standard deviation?

Recompute the diagnostics three ways on the same runs: (i) as shipped, single 5-fold; (ii) repeated
5-fold at R = 10 and R = 20, which reduces the between-repeat noise roughly as 1/sqrt(R); (iii) a
nested scheme in the spirit of Bates et al. Score within-dataset concordance for each, with the
dataset-clustered bootstrap already built in `evaluation/score_stratified.py`.

**Why this is the strong route: it cannot produce a dud.**

- If richer estimation **restores** within-dataset discrimination, Contribution 1 narrows a third
  time, and the project gains a concrete, actionable recommendation: the shipped warning fails
  because five folds is too small a sample to estimate a standard deviation from, and vendors should
  spend the compute. That is a *better* practitioner result than the current one.
- If it **does not**, Contribution 1 is far stronger than it is today. The absence of per-run signal
  would have survived a tenfold to twentyfold increase in estimation precision, which kills the most
  obvious objection to the project's headline claim and promotes it from "we did not find signal" to
  "the signal is not there to be found at this granularity."

**Secondary question, free with the same runs.** Chapter 5 flags an untested mechanism for the
*sub-chance* within-dataset figures: `G = S_CV - S_test` and `sigma_CV` are computed from the same
fold scores, so noise inflating one may deflate the other. This is confirmed in the code —
`s_cv_selected` is the mean and `sigma_cv` the standard deviation of the *same* five values. Route A
can test it directly by recomputing `G` against a mean taken from folds disjoint from those used for
the standard deviation. Resolving an anomaly the project itself raised and labelled untested is worth
a section on its own.

**Feasibility — measured, not estimated.** Timed on `bupa` (n=345, p=5): single 5-fold 183 ms;
repeated at R=10 is 9.4x, at R=20 is 17.8x. Study 2's 525 runs took about 117 s, so R=10 over the
same grid is roughly **18 minutes** and R=20 roughly **35 minutes**. Compute is not a constraint.

**It needs no new datasets.** This is the decisive practical point. The in-regime sample is exhausted
(verified: no binary PMLB dataset with n <= 500 exists outside the 44 PMLBmini candidates), which
blocks any route requiring fresh data. Route A is immune, because the comparison is *within run*:
each run is its own control, and the question is about the estimator rather than about
generalisation to new datasets.

### Route B — Dataset-level admission control

`docs/findings.md` section 9 names this as the better-supported direction: convert the strong
dataset-level signal into a go/no-go decision ("is this dataset safe to automate at all?") rather
than a per-run warning.

Honest assessment: **the right product idea, the wrong study for right now.** Demonstrating that an
admission rule *generalises* needs datasets the project does not have, and leave-one-dataset-out over
the same 25 is re-analysis that has already been partly done. It would likely produce a modest,
heavily caveated result. Better as a Chapter 7 future-work recommendation, which is where it already
sits.

### Route C — Decouple the diagnostic from the outcome

Fold into Route A as its secondary question. Not big enough to stand alone.

### Route D — An alternative uncertainty route (conformal prediction)

Compare the CV-variance diagnostics against a conformal or split-conformal risk signal.

Honest assessment: **real, but the weakest fit.** Conformal prediction is heavily published, so the
novelty would rest on the comparison rather than the method; it is a materially larger build than
Route A; and it opens a new front rather than defending the existing headline. With four chapters
unwritten this is the wrong trade.

## 4. Recommendation

**Route A, with Route C folded in.** It is the cheapest in compute, needs no data the project cannot
get, answers the single most dangerous objection to the current headline claim, resolves an anomaly
the project already flagged as open, and connects the work to two significant statistics papers that
the AutoML warning literature has not engaged with. Both possible outcomes strengthen the report.

## 5. Conditions before anything is run

1. **Write and commit the protocol first**, on its own, before any run. Pre-register the estimators,
   R values, the scoring, and an explicit statement of what result would falsify the hypothesis.
2. **Label it post-hoc where it is post-hoc.** The study is prompted by a known objection to existing
   results; the *hypothesis* is pre-registered but the *motivation* is reactive, and that should be
   said, exactly as Correction 3 is.
3. **Do not touch `build_preprocessor`.** It is imported by `evaluation/diagnostics.py` and the 861
   existing runs depend on it.
4. **The three references above must be read by the student before the FPR cites any of them**, and
   added to `docs/literature_matrix.md`'s non-plan section with the same unread flag already used for
   Peduzzi et al. and Chicco and Jurman.

## 6. The scheduling reality

Today is 2026-10-23. The FPR is due 2026-11-20 — **28 days** — and Chapters 1, 2, 4 and 7 do not
exist, which is roughly 6,700 words and the bulk of a 70% deliverable. The ethics quiz closes
2026-10-27, is a pass requirement, and cannot be extended.

Route A is defensible against that backdrop *only* because it is sub-hour compute and strengthens
the chapter that is already written rather than opening a new topic. It is not defensible if it
displaces Chapter 7 or the quiz. The honest ordering is: **ethics quiz, then the protocol and the
run (under an hour), then straight back to the chapters** — with the run's results folded into the
existing Chapter 5 and Chapter 6 as additional sections rather than written up as a separate study.
