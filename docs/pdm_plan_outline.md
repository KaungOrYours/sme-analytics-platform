# PDM Plan — content outline (working doc, not the submission)

Target: max 3 A4 pages / 1000 words, Arial/Times/Calibri 11pt. This file is longer than that on purpose — it's
the material to cut down from, not the final text. Items marked **[YOU SUPPLY]** need a real fact only you can
provide; I haven't filled those in because guessing would mean fabricating something you'd have to defend in the
viva or that Turnitin/your supervisor could flag as unverifiable.

---

## 1. Project Overview

**Title** (keep as-is, it already foregrounds the warnings angle):
Automated Data Cleaning and Model Selection for Small SME Tabular Datasets: Benchmarking Performance and
Reliability Warnings

**Background (3-4 sentences)**
- Practical origin: built an SME analytics pipeline (upload → clean → AutoML → insights) for Myanmar small
  businesses.
- The gap: AutoML, automated cleaning, and reliability/uncertainty indicators each exist as separate research
  areas; whether a pipeline's *own* warnings reliably predict when to distrust its output is comparatively
  untested — this is where the project sits.
- Lead with the warning-evaluation framing per supervisor feedback, not "I built a pipeline."

**Research question** — consider splitting into two explicit sub-questions so markers see the novelty claim
without digging for it:
- RQ1: How does the automated pipeline's performance compare to a manually tuned baseline, under identical
  splits/metrics/tuning budget, across varying dataset size and injected error type/rate?
- RQ2 (primary novelty): Do the pipeline's reliability warnings (low rows-to-features ratio, unstable
  cross-validation, suspected leakage) predict poor or unstable held-out performance — measured by precision,
  recall, and false-alarm rate?

**Objectives** (condense to 4-5 for the word budget):
1. Literature review establishing the warning-evaluation angle is genuinely differentiated from existing
   AutoML/cleaning benchmarks.
2. Evaluate cleaning via injected errors with known ground truth (detection precision/recall, reconstruction
   accuracy, per error type).
3. Benchmark automated pipeline vs. manually tuned baseline under a fixed, declared-fair protocol.
4. Score reliability warnings as binary predictors of poor outcome (precision/recall/false-alarm rate).
5. *If time allows:* runtime always logged; energy only if measurable credibly.

**References — 3+ peer-reviewed, Harvard format, alphabetical, with active links**
**[YOU SUPPLY]** — I'm not inventing titles/authors/DOIs here; that's exactly the kind of thing Turnitin and your
supervisor can check and a viva question can expose if you haven't actually read it. Search angles that map to
your actual argument, so the refs look chosen rather than bolted on:
- AutoML benchmarking / evaluation methodology for small or tabular datasets
- Automated data cleaning evaluation against ground truth / error injection methodology
- Reliability, uncertainty estimation, or "when to trust a model" literature — this one matters most since it's
  closest to your actual novelty claim
Pull these from a real database (Google Scholar, UH library, Semantic Scholar) and confirm you can explain each
one's method in the Q&A before it goes in.

---

## 2. Project Plan

**Task list with dates** (5 weeks remaining from 13 Oct to 20 Nov FPR, 23 Nov viva):

| Week | Dates | Tasks |
|---|---|---|
| 1 | 13-19 Oct | Finalize & present PDM plan (14 Oct). Targeted lit review for novelty check + the 3 references. Write `docs/evaluation_protocol.md` locking RQ wording, metrics, and a numeric definition of "poor performance" — commit it to git *before* any experiment code runs. Implement the 3 reliability-warning signals in `automl.py` (low rows-to-features, unstable CV, suspected leakage) — this was a dependency the protocol doc flagged but the schedule hadn't allocated; done 19 Oct. Draft dataset shortlist with licences in `docs/datasets.md` — candidates drafted, final confirmation still pending. |
| 2 | 20-26 Oct | Build `evaluation/` harness: per-error-type injector functions, shared comparison runner (same splits/metrics/tuning budget for both sides), warning-scoring functions. Revise for data ethics quiz (27 Oct). |
| 3 | 27 Oct - 2 Nov | Data ethics quiz (27 Oct). One-cycle timing test, then run full protocol on 3-4 deep-dive datasets. |
| 4 | 3-9 Nov | Lighter single-pass on remaining datasets. Begin drafting FPR background/methodology using confirmed facts only. |
| 5 | 10-16 Nov | Analyse results (warning precision/recall, cleaning reconstruction accuracy, comparison tables). Draft results/discussion. |
| 6 | 17-20 Nov | Final polish, formatting, code appendix. Submit FPR (20 Nov). |
| 7 | 21-23 Nov | Viva prep: rehearse explaining every parameter choice and the warning-scoring logic. Viva (23 Nov). |

Note the overlap in weeks 1, 2 and 4 (lit review / harness-building / writing running alongside each other) —
the assignment spec explicitly wants multitasking shown, not a strictly sequential plan.

**Timeline**: build this as the 1-2 weekly Excel grid the spec asks for, using the table above as the task list
and adding the three assessment dates (27 Oct, 20 Nov, 23 Nov) as fixed milestones with prep time blocked before
each.

---

## 3. Data Management Plan

**Dataset overview**
- ~10 datasets from OpenML-CC18, filtered to small scale, excluding health and personal-finance data.
- 4-6 public SME-style business datasets from the UCI Machine Learning Repository.
- Full protocol (all error types × all size levels × all seeds) on 3-4 deep-dive datasets; lighter single-pass
  on the rest — state this explicitly so the scope reads as deliberate, not incomplete.
- Per-dataset origin/country/organisation/original purpose: **[YOU SUPPLY]** once the shortlist is final — this
  level of detail belongs in `docs/datasets.md`, with just a one-line summary of the approach in the PDM plan
  itself given the 3-page limit.

**Data collection**
- OpenML-CC18: https://www.openml.org/search?type=study&study_type=task&id=99
- UCI Machine Learning Repository: https://archive.ics.uci.edu/
- Specific dataset-level URLs: **[YOU SUPPLY]** once the shortlist is final.

**Metadata**
- Formats: CSV/ARFF (OpenML), CSV (UCI).
- Record counts, feature counts, expected total size (data + code): **[YOU SUPPLY]** — depends on your final
  size filter thresholds (e.g. "under X rows, under Y features" — decide and state the actual numbers).

**Version control**
- GitHub repo: https://github.com/KaungOrYours/sme-analytics-platform (confirm this is still correct and that
  markers have access — **[YOU SUPPLY]** check sharing settings).
- Commit at least weekly; more frequently during experiment-heavy weeks (2-4).
- Suggested convention: evaluation code in `evaluation/`, dated result files
  (`results_YYYYMMDD_<dataset>.csv`), and a git tag at the commit where `evaluation_protocol.md` is frozen —
  that tag is your evidence the metrics/definition weren't adjusted after seeing results.

**ReadMe statement** (what it will contain by project end): project description, setup instructions (already
largely written), how to reproduce the evaluation experiments, dataset sources and licences, and a pointer to
`docs/ai_assistance_log.md`.

**Security & storage**
- Primary: GitHub. Backup: OneDrive. **[YOU SUPPLY]** your actual OneDrive backup cadence (e.g. weekly, synced
  automatically).
- `.env` (API key) stays out of git — confirm it's gitignored (it already is) and not shared outside your own
  machine.
- Shared with staff/markers via GitHub repo access.

**Ethics** — the four required questions, draft answers to refine once the dataset shortlist is final:
1. *GDPR?* No — all datasets are public, pre-existing, non-personal benchmark data; no personal data is
   collected directly. Health and personal-finance datasets are explicitly excluded from the shortlist.
2. *UH ethical policy?* No human subjects or primary data collection involved — likely falls under a minimal-risk
   / exempt category, but **[YOU SUPPLY]** — confirm this classification with your supervisor rather than
   self-declaring it, since the spec asks for evidence.
3. *Permission to use?* Yes, provided each dataset's licence is checked and documented before use (OpenML and
   UCI both state reuse terms per dataset) — this check happens in `docs/datasets.md`, not assumed.
4. *Ethically collected originally?* To be verified per dataset as part of the selection criteria — any dataset
   without clear provenance gets excluded, not included with a caveat.

---

## What I didn't write for you

Real reference citations, per-dataset metadata/URLs, your OneDrive cadence, and the UH ethics classification —
all of these need a fact only you have or a check only you (or Rama) can perform. Everything else here is ready
to compress into the 3-page/1000-word submission format.
