# SME Analytics Platform

**Automated Business Intelligence for Myanmar Small & Medium Enterprises**

Upload your Excel or CSV file and receive instant automated analysis — no technical knowledge required. Everything is processed in memory and permanently deleted after your session.

---

## Overview

Small business owners in Myanmar have valuable data sitting unused in Excel files. This platform transforms that raw data into actionable business insights automatically, replacing the need for a dedicated data analyst.

**Core Promise:** Upload your file. Get insights. In 30 seconds. For free.

---

## Features

**Data Processing**
- Automatic data cleaning with quality scoring (0-100%)
- Duplicate removal and missing value handling
- Smart date format standardization
- Currency symbol cleaning (ks, MMK, $)
- Boolean value normalization (Yes/No to 1/0)
- Readable column name generation

**Machine Learning**
- Automatic problem type detection (classification, regression, clustering, time series)
- Multi-model AutoML with best model selection
- Feature importance analysis
- Sales forecasting with 5-period outlook
- Session-based model training (deleted after use)

**Analytics & Visualization**
- Interactive histograms and bar charts (Plotly)
- Plain English business insights
- Detailed statistical breakdown
- Data quality comparison (before vs after cleaning)

**AI Business Advisor**
- Powered by Groq (LLaMA 3.3 70B)
- Ask questions about your data in plain English
- Receive actionable business recommendations

**Report Generation**
- Professional PDF report download
- Includes model results, insights, statistics, and data preview

**Privacy**
- Zero data retention — nothing is saved to any database
- All processing occurs in memory
- Files and models are deleted immediately after each session

---

## Machine Learning Models

| Problem Type | Models | Use Case |
|---|---|---|
| Classification | Random Forest, Logistic Regression, Decision Tree, Gradient Boosting | Predict categories (churn, risk) |
| Regression | Random Forest, Linear Regression, Ridge | Predict values (price, revenue) |
| Clustering | K-Means (3 clusters) | Group similar customers or products |
| Time Series | Linear Trend Forecasting | Forecast future sales |

---

## Supported File Formats

| Format | Extensions | Max Size |
|---|---|---|
| Excel | .xlsx, .xls | 10MB |
| CSV | .csv | 10MB |

---

## Tech Stack

**Frontend**
- React 18 + Vite
- Tailwind CSS
- Plotly.js
- Axios

**Backend**
- FastAPI (Python 3.13)
- pandas + numpy
- scikit-learn
- ReportLab
- Groq API

---

## Getting Started

### Prerequisites
- Python 3.10 or higher
- Node.js 18 or higher
- Git

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file inside the `backend` folder:

```
GROQ_API_KEY=your_groq_api_key_here
```

Start the backend server:

```bash
uvicorn main:app --reload
```

Backend runs at: http://localhost:8000  
API documentation: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: http://localhost:5173

---

## Project Structure

```
sme-analytics-platform/
├── backend/
│   ├── main.py                 FastAPI application and endpoints
│   ├── requirements.txt        Python dependencies
│   ├── .env                    Environment variables (not committed)
│   └── services/
│       ├── cleaner.py          Automated data cleaning pipeline
│       ├── analyzer.py         Statistics and insight generation
│       ├── automl.py           ML model training and selection
│       └── reporter.py         PDF report generation
├── frontend/
│   ├── src/
│   │   ├── App.jsx             Main application component
│   │   └── components/
│   │       ├── FileUpload.jsx
│   │       ├── QualityScore.jsx
│   │       ├── CleaningReport.jsx
│   │       ├── ProblemType.jsx
│   │       ├── MLResults.jsx
│   │       ├── Insights.jsx
│   │       ├── Statistics.jsx
│   │       ├── Charts.jsx
│   │       └── AIExplanation.jsx
│   └── package.json
├── render.yaml                 Render deployment configuration
└── README.md
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | / | Project info and status |
| GET | /health | Health check |
| POST | /upload | Main analysis endpoint |
| POST | /explain | AI explanation via Groq |
| POST | /generate-report | PDF report download |

---

## System Flow

```
User uploads Excel or CSV
         |
         v
File validation (format, size, content)
         |
         v
Automatic data cleaning
         |
         v
Data quality scoring
         |
         v
Problem type detection
         |
         v
AutoML model training
         |
         v
Chart generation
         |
         v
Insight and statistics generation
         |
         v
AI explanation (Groq)
         |
         v
PDF report available for download
         |
         v
All data and models deleted
```

---

## Deployment

**Backend:** Render (Free tier)  
**Frontend:** Vercel (Free tier)

Environment variables required on Render:

| Key | Description |
|---|---|
| GROQ_API_KEY | Your Groq API key from console.groq.com |

---

## Roadmap

- Paper document scanner with image upload
- Custom Burmese handwriting OCR model (research contribution)
- Myanmar language output
- Federated learning for privacy-preserving collective intelligence
- Transfer learning for improved accuracy on small datasets
- Mobile responsive improvements

---

## Author

**Kaung Htet**  
Master's Student | IEEE RASSE 2025 Presenter  
GitHub: https://github.com/KaungOrYours  
Repository: https://github.com/KaungOrYours/sme-analytics-platform

---

## License

MIT License. Free to use, modify, and distribute.

---

*Built for Myanmar SMEs — empowering small businesses through accessible data analytics.*