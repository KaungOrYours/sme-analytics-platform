> **SUPERSEDED 2026-10-19.** The PDM plan actually submitted and approved by Dr. Rama
> (`Project and Data Management Plan (Kaung Htet).pdf`, 14 Oct) uses 7 different, already-read, already-cited
> references — see `docs/literature_matrix.md`. None of the 3 candidates below were used in the approved plan.
> Left here only as a record of what was searched before the submitted plan was shared with this session; do
> not cite from this file.

# Reference candidates — drafted 2026-10-19, NOT yet verified by the student

Found via web search against the three angles in `docs/pdm_plan_outline.md` Section 1 (AutoML
benchmarking for small tabular data; automated cleaning evaluation against ground truth; reliability/
uncertainty estimation — the one closest to the actual novelty claim).

**These are real, searchable papers with real DOIs — not fabricated — but per `CLAUDE.md` Section 3,
nothing goes in the PDM plan or FPR until the student has actually opened the paper, confirmed the
citation details below are accurate from the primary source, and can explain its method in the viva.**
Treat this file as a shortlist to read, not a finished reference list.

## 1. Reliability / uncertainty estimation (closest to the novelty claim — read this one first)

Tyralis, H. and Papacharalampous, G. (2024) 'A review of predictive uncertainty estimation with machine
learning', *Artificial Intelligence Review*, 57(4). doi: 10.1007/s10462-023-10698-8.
Open access: https://link.springer.com/article/10.1007/s10462-023-10698-8

Why it's a plausible fit: a peer-reviewed survey (Springer) of uncertainty-estimation methods for ML
predictions — covers the "when should a model's output be trusted" question the RQ2 warnings-evaluation
sits inside. Check: it's a survey, not an empirical study — may be better as framing/background than as
a methodological template to copy. Look for a more empirical, applied companion reference if the report
needs one that actually scores warnings against outcomes the way this project does.

## 2. AutoML benchmarking on small tabular data

Conrad, F., Mälzer, M., Schwarzenberger, M., Wiemer, H. and Ihlenfeldt, S. (2022) 'Benchmarking AutoML
for regression tasks on small tabular data in materials design', *Scientific Reports*, 12, 19350.
doi: 10.1038/s41598-022-23327-1.
Open access: https://www.nature.com/articles/s41598-022-23327-1

Why it's a plausible fit: peer-reviewed, open access, directly benchmarks AutoML frameworks against
manual optimisation on small datasets (<1000 rows) — close in spirit to this project's RQ1 (automated
vs. manually tuned baseline). Domain is materials science, not SME/business data — the report should
note that explicitly as a scope difference, not imply the domains match.

## 3. Automated data-cleaning evaluation against ground truth

Abdelaal, M., Hammacher, C. and Schöning, H. (2023) 'REIN: A comprehensive benchmark framework for data
cleaning', in *Proceedings of the 26th International Conference on Extending Database Technology
(EDBT)*, pp. 499-511.
PDF: https://openproceedings.org/2023/conf/edbt/3-paper-49.pdf

Why it's a plausible fit: peer-reviewed conference paper, benchmarks 38 error detection/repair methods
across 14 public datasets against downstream ML model performance — same shape as this project's cleaning
evaluation (detection precision/recall + downstream effect), just at larger scale. Good source for citing
*how* to structure a detection-precision/recall evaluation, even if this project's error-injection protocol
differs in specifics (per-error-type injection at 5/10/20%, per `docs/evaluation_protocol.md` Section 3).

## Other candidates surfaced but not chosen (weaker fit, listed for completeness)

- Shi, X. et al., 'Benchmarking Multimodal AutoML for Tabular Data with Text Fields' (NeurIPS Datasets &
  Benchmarks, 2021) — AutoML benchmarking, but multimodal/text focus is a tangent from this project's
  scope.
- 'A Structured Review of Literature on Uncertainty in Machine Learning & Deep Learning' (arXiv) — broader
  uncertainty survey, but arXiv preprint status needs checking against the module's peer-review
  requirement before use.

## What's still needed before these go in the PDM plan

1. Student reads all three primary sources (not just this summary) and confirms the method descriptions
   above are accurate.
2. Confirm Harvard format is actually what the module wants — `MEMORY.md` flagged a Harvard-vs-IEEE
   conflict on 2026-10-14 between the module spec and an earlier docx draft; still unresolved as of this
   write-up.
3. Decide if 3 is enough or if a 4th (e.g. a more empirical uncertainty-estimation paper, to pair with
   the Tyralis & Papacharalampous survey) strengthens the RQ2 framing.
