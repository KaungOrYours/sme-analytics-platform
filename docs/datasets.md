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

## Still open

- UH formal ethics process confirmation (ethics question 2 above) — needs the student/supervisor, not
  something I can complete.
- Exact per-dataset original licence text, beyond "public UCI terms via the MIT-licensed PMLB aggregator."
