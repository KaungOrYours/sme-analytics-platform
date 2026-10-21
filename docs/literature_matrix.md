# Literature matrix

Transcribed from the approved PDM plan (`Project and Data Management Plan (Kaung Htet).pdf`, submitted and
approved by Dr. Rama, 2026-10-14). This is the project's PDM Objective 1 deliverable: demonstrate that the
predictive validity of low-overhead AutoML diagnostics (n/p, σ_CV) against the specific operational outcome
defined in `docs/evaluation_protocol.md` (RQ2) is not already established in the literature — a closest-paper
comparison, not a general-purpose literature review.

These are the project's locked references. Nothing here is a candidate — all 7 were read and cited in the
approved plan. `docs/references_candidates.md` (an earlier, superseded candidate list found before the
submitted plan was shared with this session) should not be used; see that file's note.

| Ref | Key finding | Relevance to this project |
|---|---|---|
| Santos, Cardoso & Alves (2023) | A reliability-classifier trained using the real OpenML 21 datasets | Closest comparator; differs in its definition of failure |
| Lahoti, Gummadi & Weikum (2023) | Risk Advisor: failure-risk estimation using a trained meta-learner | Representative of the class of projects requiring a secondary trained model, which this project deliberately does not |
| Gijsbers et al. (2024) | AMLB: a large multi-framework AutoML benchmark | Shows evaluation is a valid contribution in this literature; RQ1 (the automated-vs-manual benchmark) is not a significant gap on its own — RQ2 is the actual novelty |
| Knauer, Grimm & Rodner (2024) | PMLBmini: 44 classification datasets with n <= 500 | The dataset source for this project (compatible scale; not OpenML-CC18, which is not small-data) |
| Cawley & Talbot (2010) | Optimistic bias from reusing a test set during model/threshold selection | Motivates freezing all thresholds (including delta_G) before any outcome is observed |
| Alteryx (n.d.) | EvalML's `AutoMLSearch._check_for_high_variance` ships a high-variance cross-validation warning | The warning exists in a real AutoML framework but its predictive validity has never been tested — this is the literal gap RQ2 fills |
| Paraschakis, Castellani, Borboudakis & Tsamardinos (2024) | Confidence-interval estimation of AutoML performance under winner's-curse bias | Source for the bootstrap-CI treatment of uncertainty on G, not just the delta_G threshold value |

## Full references (Harvard, as submitted)

Santos, V. C. A., Cardoso, L. and Alves, R. (2023) 'The quest for the reliability of machine learning models
in binary classification on tabular data', *Scientific Reports*, 13, Art. No. 18464.

Lahoti, P., Gummadi, K. P. and Weikum, G. (2023) 'Responsible model deployment via model-agnostic
uncertainty learning', *Machine Learning*, 112(3), pp. 939-970.

Gijsbers, P. et al. (2024) 'AMLB: an AutoML Benchmark', *Journal of Machine Learning Research*, 25(101),
pp. 1-65.

Knauer, R., Grimm, M. and Rodner, E. (2024) *PMLBmini: A Tabular Classification Benchmark Suite for
Data-Scarce Applications* (arXiv:2409.01635). Available at: https://arxiv.org/abs/2409.01635 (Accessed: 14
October 2026).

Cawley, G. C. and Talbot, N. L. C. (2010) 'On over-fitting in model selection and subsequent selection bias
in performance evaluation', *Journal of Machine Learning Research*, 11, pp. 2079-2107.

Alteryx (n.d.) *AutoMLSearch._check_for_high_variance — EvalML documentation*. Available at:
https://evalml.alteryx.com/en/stable/_modules/evalml/automl/automl_search.html (Accessed: 14 October 2026).

Paraschakis, K., Castellani, A., Borboudakis, G. and Tsamardinos, I. (2024) 'Confidence Interval Estimation
of Predictive Performance in the Context of AutoML', *Proceedings of Machine Learning Research*, vol. 256.
Paris, France: PMLR.

---

## Additional references cited in the evaluation protocol (NOT from the approved plan)

Added 2026-10-21. These two are cited in `docs/evaluation_protocol.md` to justify frozen thresholds
but are **not among the 7 locked references above**, so they were not part of the approved plan's
literature review. Both have been verified as real, correctly-attributed publications. **Neither has
been read by the student yet.** Read both before the FPR cites them, per `CLAUDE.md` Section 3 — and
note the attribution caveat on the second one, which is not a formality.

**Peduzzi, P., Concato, J., Kemper, E., Holford, T. R. and Feinstein, A. R. (1996) 'A simulation
study of the number of events per variable in logistic regression analysis', *Journal of Clinical
Epidemiology*, 49(12), pp. 1373-1379.**

- Verified: PubMed 8970487. A Monte Carlo simulation based on a cardiac trial of 673 patients with
  252 deaths and seven predictors (EPV = 36 in the full sample), drawing 500 samples at EPV levels
  of 2, 5, 10, 15, 20 and 25 and comparing bias, precision and significance testing against the
  full-sample model.
- Finding: at EPV of 10 or greater no major problems occurred; below 10, regression coefficients were
  biased in both the positive and negative directions.
- **Supports the `n/p < 10` anchor well.** The paper's own threshold is 10, the direction of its
  finding is the one this project assumes, and the quantity (events per variable) maps onto n/p here.
  Usable as cited once read.

**Chicco, D. and Jurman, G. (2020) 'The advantages of the Matthews correlation coefficient (MCC)
over F1 score and accuracy in binary classification evaluation', *BMC Genomics*, 21, Art. No. 6.
doi: 10.1186/s12864-019-6413-7.**

- Verified: real paper, correct journal, volume and article number.
- Finding: accuracy and F1 can give over-optimistic inflated results on imbalanced data, while MCC
  scores high only when all four confusion-matrix cells are good; the authors argue MCC should be
  preferred for binary classification evaluation.
- **Attribution caveat — this matters.** `evaluation_protocol.md` Section 6 originally cited this
  paper as recommending **MCC = 0 for degenerate confusion matrices**. That specific recommendation
  could not be confirmed to be in this paper, whose subject is MCC versus F1 and accuracy, not
  zero-denominator edge cases. The paper **does** directly support the separate and more important
  claim that MCC is the right headline metric under class imbalance, which is how the methodology
  chapter now uses it. The MCC = 0 convention itself now rests on scikit-learn's verified behaviour
  instead — see the protocol's 2026-10-21 correction note. Do not cite this paper for the
  edge-case rule without first finding the recommendation in its text.
