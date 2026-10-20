# Dataset manifest — locked 2026-10-19

Supersedes the earlier draft (OpenML-CC18 + UCI candidates) written before the approved PDM plan was shared
with this session. Per the approved `Project and Data Management Plan (Kaung Htet).pdf` (submitted and
approved by Dr. Rama, 14 Oct): 6-8 datasets from **PMLBmini** (Knauer, Grimm and Rodner, 2024,
arXiv:2409.01635), a benchmark suite purpose-built for small-sample (n<=500) binary classification.

**Source used**: [TabMini](https://github.com/RicardoKnauer/TabMini), the same authors' actively-maintained,
ethically-curated successor to raw PMLBmini — it already excludes datasets that are deprecated, derived from
time series/images, outliers, ethically sensitive, or contain personally identifiable information (25 of the
original 44 survive this screening). Using the pre-screened set directly satisfies this project's own ethics
criterion ("screened for identifiability, excluded if it cannot be ruled out that the data is personal") more
defensibly than hand-picking from the raw 44. Fetched via the `pmlb` Python package (MIT-licensed; aggregates
public UCI/OpenML-sourced datasets — per-dataset original provenance is noted below where documented by
PMLB/TabMini, flagged "needs confirming" where it is not).

All metadata below was pulled live via `pmlb.fetch_data(<name>)` on 2026-10-19, not asserted from memory —
see the Verification section at the bottom for how to reproduce it.

## Selection

7 datasets selected from TabMini's 25, chosen to span a wide range of n/p (sample-to-feature ratio) —
essential for RQ2 to have any statistical power to detect whether n/p and sigma_CV actually discriminate
poor outcomes, since a sample with uniformly high or uniformly low n/p would give the diagnostics nothing to
discriminate between. Domain-diversified deliberately (not all health), though the approved plan's ethics
criterion is identifiability, not domain, so health-domain datasets are not excluded on principle.

Split into disjoint **development** (protocol-freezing, pilot, RQ1/RQ2) and **final-evaluation** (RQ3
transfer test) groups, predetermined now, before any experiment runs — stratified by n/p rank so neither
group is skewed toward only-easy or only-hard cases.

| Dataset | Group | n | p (raw) | p (used) | n/p (used) | Classes (counts) | Missing | Domain |
|---|---|---|---|---|---|---|---|---|
| `molecular_biology_promoters` | development | 106 | 57 | 57 | 1.86 | 2 (53/53) | 0 | genomics |
| `labor` | final-evaluation | 57 | 16 | 16 | 3.6 | 2 (37/20) | 0 | economics/negotiation |
| `appendicitis` | development | 106 | 7 | 7 | 15.1 | 2 (85/21) | 0 | medical diagnosis |
| `mux6` | final-evaluation | 128 | 6 | 6 | 21.3 | 2 (64/64) | 0 | synthetic (6-bit multiplexer) |
| `biomed` | development | 209 | 8 | **5** | 41.8 | 2 (134/75) | 0 | clinical lab measurements |
| `bupa` | final-evaluation | 345 | 5 | 5 | 69.0 | 2 (176/169) | 0 | liver function blood tests |
| `irish` | development | 500 | 5 | 5 | 100.0 | 2 (278/222) | 0 | education/sociology |

`p (used)` differs from `p (raw)` only for `biomed`: 3 of its 8 raw columns (`Observation_number`,
`Hospital_identification_number_for_blood_sample`, `Date_that_blood_sample_was_taken`) are record
IDs/metadata, not predictive features — found by inspecting actual column values (191 near-unique values in
the "hospital identification number" column across 209 rows). **Frozen rule, stated before any experiment
runs**: these 3 columns are dropped for every pipeline run on `biomed`, automated and manual alike, so both
sides see the same 5 real features (`Age_of_patient`, `ml`, `m2`, `m3`, `m4`).

Development group: `molecular_biology_promoters`, `appendicitis`, `biomed`, `irish` (n/p: 1.86, 15.1, 41.8, 100)
Final-evaluation group: `labor`, `mux6`, `bupa` (n/p: 3.6, 21.3, 69.0)

## Per-dataset detail

| Identifier | Source URL | Version/provenance | Licence | Target variable | Exclusion/preprocessing notes |
|---|---|---|---|---|---|
| `molecular_biology_promoters` | https://github.com/RicardoKnauer/TabMini (fetched via `pmlb`) | UCI Molecular Biology (Promoter Gene Sequences); original source UCI ML Repository | Public/UCI terms (PMLB aggregator: MIT) | `target` (promoter / non-promoter) | None beyond standard encoding |
| `labor` | same | UCI/OpenML "labor" (Canadian labour negotiations, 1987-88) | Public/UCI terms | `target` (good/bad settlement) | None |
| `appendicitis` | same | UCI/OpenML "appendicitis" | Public/UCI terms | `target` | None |
| `mux6` | same | Synthetic 6-bit multiplexer (classic ML benchmark, not derived from real-world data) | Public domain (synthetic) | `target` (multiplexer output) | None |
| `biomed` | same | Classic UCI "biomed" (clinical chemistry study) | Public/UCI terms | `target` (carrier/non-carrier) | **Drop `Observation_number`, `Hospital_identification_number_for_blood_sample`, `Date_that_blood_sample_was_taken` before use — see note above** |
| `bupa` | same | UCI "bupa"/"liver-disorders" (BUPA Medical Research Ltd.) | Public/UCI terms | `target` (liver disorder indicator) | None |
| `irish` | same | "irish" (Irish primary-school leavers survey, sociology/education research, long-standing public benchmark) | Public/UCI terms | `target` | `Sex` is a sensitive-category feature; dataset is long-standing aggregate survey data with no plausible re-identification path — reviewed under the GDPR-screening criterion below, not excluded |

## Ethics (per the approved plan's 4 questions)

1. **GDPR/identifiability**: all 7 datasets are decades-old, publicly redistributed aggregate research
   datasets (UCI/PMLB), already screened by TabMini's own curation to exclude PII. `biomed`'s "hospital
   identification number" is a lab-sample tracking ID from a 1980s study, not a real-world identifier, and
   is dropped from modeling regardless (see above). No dataset here permits re-identifying an individual —
   screening criterion satisfied.
2. **UH ethical policy**: per the approved plan, self-declaration is explicitly stated as insufficient —
   **still needs confirmation via UH's formal ethics process**, not something this session can complete.
   Flagging as the one open ethics item.
3. **Permission to use**: PMLB is MIT-licensed as an aggregator; underlying datasets are long-established
   public UCI/OpenML-sourced benchmarks with permissive reuse terms. Exact per-dataset original licence
   text (as opposed to "public UCI terms") is marked "needs confirming" above where not directly verified —
   do this before the FPR cites it as fact.
4. **Ethical original collection**: all 7 are long-standing, widely-cited ML benchmark datasets with no
   known provenance concerns; none flagged by TabMini's own ethical curation pass.

## Verification (how this was produced, so it's reproducible)

```
pip install pmlb
python3 -c "from pmlb import fetch_data; df = fetch_data('appendicitis'); print(df.shape)"
```

Dataset list and exclusion rationale (PII/deprecated/time-series-derived/outlier/ethically-sensitive) come
from `tabmini/data/data_info.py` in the TabMini repo (https://github.com/RicardoKnauer/TabMini), inspected
directly on 2026-10-19, not asserted from memory.

## Known data property: `irish`'s `Educational_level` perfectly determines `target`

Found 2026-10-20 while running the full development-group protocol: the automated pipeline (Random Forest)
scored AUROC = 1.0 on both CV and test, for all 3 seeds, at the clean (0% corruption) condition — `sigma_cv`
and `G` both exactly 0. Per `CLAUDE.md`'s "treat 99-100% accuracy as a bug until proven otherwise" rule, this
was investigated rather than accepted.

**Verified cause**: a crosstab of `Educational_level` x `target` across all 500 rows shows a perfect,
exceptionless partition — every row with `Educational_level` in {0, 1, 10} has `target=1`; every row with
`Educational_level` in {2, 3, ..., 9} has `target=0`. This is leakage intrinsic to the raw PMLB `irish`
dataset, not a bug in this project's pipeline code. The partition is non-monotonic in the raw integer coding,
which is why the two pipelines diverge sharply on this dataset:
- **Manual baseline (logistic regression)** treats `Educational_level` as a single continuous numeric feature
  (PMLB stores it as an int column, so `build_preprocessor` routes it to the numeric/scaled branch, not
  one-hot). A single linear decision boundary cannot carve out {0, 1, 10} while excluding {2..9}, so logistic
  regression only partially exploits the leak — S_test lands at a believable 0.82-0.90 across seeds.
- **Automated pipeline (Random Forest, selected by CV)** uses threshold splits and can carve out the
  non-monotonic partition exactly, reaching AUROC = 1.0 on every fold and on the test set, every seed.

**Decision (student, 2026-10-20): keep `irish` unchanged in the dataset manifest — do not drop the column or
swap the dataset.** Report the saturation as a finding rather than engineering it away, since it is a genuine,
unforced illustration of the dissertation's own thesis: an automated pipeline with no human feature review can
silently exploit a leaking feature that a simpler model cannot, and would do so undetected in RQ1/RQ2's own
formal diagnostics (`n/p`, `sigma_cv`) once `sigma_cv` collapses to 0 at saturation, since a diagnostic with
no variance in its own CV scores gives no warning signal by construction. Explicitly tie this to the live
app's `suspected_leakage` warning in `backend/services/automl.py` (CV-score ceiling 0.98) — a feature
excluded from the formal RQ1-3 evaluation per `docs/literature_matrix.md` ("no valid, deployable leakage
detector found in the literature"), but which *would* have fired here (1.0 > 0.98), had it been in scope.
This is worth a discussion-section paragraph: the formal evaluation's own exclusion of a leakage diagnostic
is itself tested by a real case where exactly that kind of signal was the one thing that mattered.

Practical effect on scoring: at the clean condition, `irish`'s automated-pipeline runs have `sigma_cv=0`,
which means the `sigma_cv > 0.10` diagnostic by construction does not (and structurally cannot) trigger on a
saturated run — these 3 runs are non-poor by the frozen `G > 0.05` definition (G=0) despite the underlying
result being arguably the least trustworthy in the whole development group. Flag this explicitly when
reporting RQ2 precision/recall: it is a real limitation of a purely statistical optimism-gap diagnostic, not
a scoring bug.

## Still open

- UH formal ethics process confirmation (ethics question 2 above) — needs the student/supervisor, not
  something I can complete.
- Exact per-dataset original licence text, beyond "public UCI terms via the MIT-licensed PMLB aggregator."
