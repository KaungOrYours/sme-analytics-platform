# SME Analytics Platform

Upload a CSV or Excel file and get automated cleaning, a data-quality score, problem-type detection,
model selection, charts and plain-English insights. Built for small and medium enterprises that have
useful data sitting in spreadsheets and no analyst to work it.

This repository is also the artefact for an MSc Data Science final project at the University of
Hertfordshire. The application is the system under study; the research asks a narrower question
about it, and that work is summarised under [Research](#research) below.

---

## Overview

The pipeline is deliberately transparent rather than magical. Every cleaning action is logged and
returned, every model that was tried is reported alongside the one that won, and the pipeline emits
reliability warnings about its own output. Where it cannot tell which kind of problem a dataset
represents, it says so and names the alternative instead of silently picking one.

---

## Features

**Data cleaning**
- Duplicate removal, missing-value handling, and type-consistency repair
- Currency and separator cleaning (`1,200,000 MMK` becomes `1200000`)
- Date parsing and format standardisation
- Boolean normalisation (Yes/No to 1/0)
- Inconsistent-category detection (`Yangon` / `yangon` / ` Yangon ` reported as one group)
- Outlier handling that separates Tukey's inner and outer fences: only far-out values are
  winsorised, never deleted, and never on fewer than 20 rows, where the fences are too unstable to
  justify modifying data
- Readable column-name generation
- Every action recorded in a cleaning report returned with the response

**Data quality**
- A 0-100 score with a per-dimension breakdown (completeness, uniqueness, type consistency)
- Before-and-after comparison
- The score is an unvalidated project heuristic, not a validated metric, and is documented as such

**Machine learning**
- Problem-type detection (classification, regression, clustering, time series) with a confidence
  value and, where the evidence is weak, a named alternative
- Model selection by cross-validated score, with preprocessing fitted inside the cross-validation
  folds so the test partition is touched once, at the end
- Categorical features are one-hot encoded, not dropped
- All candidate model scores returned, not just the winner's
- Reliability warnings: low rows-to-features ratio, unstable cross-validation, suspected leakage
- Sales forecasting with a five-period outlook and an approximate interval from backtest residuals,
  labelled approximate because it is not a formal prediction interval

**Analytics**
- Histograms, bar charts and a numeric correlation heatmap (Plotly)
- Plain-English insights and a statistical breakdown

**No hyperparameter search.** Models run at library defaults with a fixed `n_estimators=50`. This is
a deliberate, documented property, not an oversight: the gap between default-configured automation
and a tuned baseline is one of the things the research measures.

---

## Models

| Problem type | Models tried | Selection |
|---|---|---|
| Classification | Random Forest, Logistic Regression, Decision Tree, Gradient Boosting | Cross-validated score |
| Regression | Random Forest, Linear Regression, Ridge | Cross-validated score |
| Clustering | K-Means, fixed at 3 clusters | Not applicable |
| Time series | Linear trend with held-out backtest | Not applicable |

Clustering is numeric-only; mixed-type distance metrics such as Gower are out of scope.

---

## Data handling and limits

Uploaded files are processed entirely in memory. Nothing is written to persistent storage, logged,
or sent to a third party, and nothing is retained after the response is returned. The service holds
no API keys or credentials.

| Limit | Value |
|---|---|
| Upload size | 10 MB, enforced during a chunked read so an oversized payload is never fully materialised |
| Uncompressed size (`.xlsx` is a zip) | 100 MB, with a compression-ratio check before the workbook is expanded |
| Parsed shape | 50,000 rows, 200 columns |
| Rate limit | 10 uploads per minute per client |
| Accepted formats | `.csv`, `.xlsx`, `.xls` — determined from file content, then cross-checked against the extension |

Threat model, the controls behind each limit, and an explicit list of what they do **not** protect
against are in [SECURITY.md](SECURITY.md).

---

## Research

The dissertation does not claim the pipeline as a research contribution. It asks whether an
automated pipeline's built-in reliability warnings predict its own failures — the kind of warning
that ships in production AutoML software and, as far as the reviewed literature shows, has not been
empirically validated.

Three pre-registered studies were run, totalling 861 pipeline runs over 33 datasets, plus one
post-hoc re-analysis of those runs. Two of the project's own conclusions were overturned by its own later work,
and both corrections are reported in sequence rather than hidden.

**Start here: [`docs/findings.md`](docs/findings.md)** — the consolidated position across all
studies. The individual study records each carry a banner stating what in them has been superseded.

| Document | Contents |
|---|---|
| [`docs/findings.md`](docs/findings.md) | Consolidated final position, the correction sequence, limitations, provenance audit |
| [`docs/evaluation_protocol.md`](docs/evaluation_protocol.md) | Study 1 design, frozen before any run |
| [`docs/study2_protocol.md`](docs/study2_protocol.md) / [`results`](docs/study2_results.md) | 25 datasets, untouched confirmation holdout |
| [`docs/study3_protocol.md`](docs/study3_protocol.md) / [`results`](docs/study3_results.md) | Threshold recalibration and external transfer |
| [`docs/stratified_reanalysis.md`](docs/stratified_reanalysis.md) | Between- versus within-dataset discrimination; dataset-clustered intervals |
| [`docs/datasets.md`](docs/datasets.md) | Dataset manifest, selection criteria, licences, ethics screening |
| [`docs/literature_matrix.md`](docs/literature_matrix.md) | Closest-paper comparison |

All evaluation code is in `evaluation/`, separate from the application, with fixed seeds and results
written to JSON. It imports the application's own preprocessing rather than reimplementing it, so
what is evaluated is the real pipeline. Superseded harness files from an earlier design are retained
with banners explaining why, rather than deleted.

---

## Tech stack

**Backend** — FastAPI, pandas, scikit-learn, numpy, openpyxl (Python 3.13)
**Frontend** — React 19, Vite, Tailwind CSS 4, Plotly.js, Axios
**Testing** — pytest
**Deployment** — Render (backend), Vercel (frontend)

Python dependencies are pinned to exact versions. Dependabot is configured for both pip and npm.

---

## Getting started

Developed and tested on Python 3.13 and Node 18+.

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Runs at http://localhost:8000, with interactive API docs at http://localhost:8000/docs.
No environment variables are required.

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

Runs at http://localhost:5173.

### Tests and linting

```bash
cd backend && venv/bin/python3 -m pytest tests     # must be run from backend/, where pytest.ini lives
cd frontend && npx eslint src && npm run build
```

### Reproducing the research

```bash
python3 -m evaluation.full_run development          # Study 1
python3 -m evaluation.full_run_study2 B             # Study 2 exploratory group
python3 -m evaluation.score_stratified all          # stratified re-analysis
```

See [`evaluation/README.md`](evaluation/README.md). Datasets are fetched on demand and are not
committed.

---

## API

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Service info |
| GET | `/health` | Health check |
| POST | `/upload` | Upload a file and receive the full analysis |

`POST /upload` returns the cleaned preview, quality scores and per-dimension breakdown, detected
problem type, AutoML results including every candidate score and the reliability warnings, chart
data, insights, statistics and the cleaning report. Errors return a real status code with a message:
`400` for an unusable file, `413` for one that is too large, `429` when rate-limited.

---

## Project structure

```
backend/
  main.py                 FastAPI app, endpoints, upload orchestration
  security.py             Upload limits, format detection, rate limiting, filename sanitising
  services/
    cleaner.py            Problem detection, automated cleaning, quality scoring
    analyzer.py           Statistics and insight generation
    automl.py             Problem-type routing, model selection, reliability warnings
  tests/                  pytest suite for cleaner.py and security.py
frontend/
  src/App.jsx             Single-page flow
  src/components/         FileUpload, QualityScore, CleaningReport, ProblemType,
                          MLResults, Insights, Statistics, Charts
evaluation/               Research harness, separate from the application
docs/                     Protocols, results, dataset manifest, literature matrix
SECURITY.md               Threat model, controls, and stated limitations
render.yaml               Render deployment configuration
```

---

## Known gaps

Stated rather than left to be discovered.

- No continuous integration. Tests cover `cleaner.py` and `security.py`; `main.py`, `automl.py` and
  `analyzer.py` have no direct tests, and there are no frontend tests.
- No hyperparameter search anywhere in the application (see Features).
- The quality score is an unvalidated heuristic.
- Clustering is numeric-only and fixed at three clusters.
- The rate limiter is per process and will not stop a distributed attack.

---

## Out of scope

Recorded so the project's boundaries are explicit, not as a near-term roadmap: document scanning and
Burmese handwriting OCR, Myanmar-language output, Google Sheets import, federated and transfer
learning, and real-user usability testing, which would require formal UH ethics approval.

---

## Development notes

AI-assisted tooling was used during development for parts of the code and project documentation,
under supervisor-approved academic use. A detailed assistance record is maintained privately and
available on request.

---

## Author

**Kaung Htet** — MSc Data Science, University of Hertfordshire. IEEE RASSE 2025 presenter.
GitHub: https://github.com/KaungOrYours
Repository: https://github.com/KaungOrYours/sme-analytics-platform

---

## License

[Prosperity Public License 3.0.0](https://prosperitylicense.com/versions/3.0.0). Free for
noncommercial use — research, personal, educational, nonprofit and government. Commercial use gets a
free 30-day trial, after which it requires a separate commercial licence from the contributor. See
[LICENSE](LICENSE).
