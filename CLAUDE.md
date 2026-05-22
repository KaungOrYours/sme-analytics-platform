PROJECT: SME Analytics Platform
GitHub: github.com/KaungOrYours/sme-analytics-platform
DEVELOPER:
- Name: Kaung Htet (KaungOrYours)
- Master's student in singapore
- M2 MacBook Pro 8GB RAM
- Python 3.13.7, Node 23.7.0
- VS Code + GitHub Copilot (student pack)

PROJECT DESCRIPTION:
Zero-touch automated business intelligence
platform for Myanmar SMEs.
User uploads Excel/CSV → gets instant
automated analysis.
Everything processed in memory.
Nothing saved. Stateless design.
CURRENT STATUS:
- Working full stack web application
- Frontend: React + Vite + Tailwind CSS
  Running on localhost:5173 or 5174
- Backend: FastAPI + Python
  Running on localhost:8000
PROJECT STRUCTURE:
sme-analytics-platform/
├── backend/
│   ├── main.py (FastAPI app)
│   ├── requirements.txt
│   ├── venv/ (Python virtual env)
│   └── services/
│       ├── cleaner.py
│       ├── analyzer.py
│       ├── automl.py
│       └── reporter.py (new)
├── frontend/
│   ├── src/
│   │   ├── App.jsx (main component)
│   │   └── components/
│   │       ├── FileUpload.jsx
│   │       ├── QualityScore.jsx
│   │       ├── CleaningReport.jsx
│   │       ├── ProblemType.jsx
│   │       ├── MLResults.jsx
│   │       ├── Insights.jsx
│   │       ├── Statistics.jsx
│   │       └── Charts.jsx
│   ├── package.json
│   └── vite.config.js
└── README.md
TECH STACK:
Frontend: React 18 + Vite + Tailwind CSS
          Plotly.js (plotly.js-dist-min)
          Axios
Backend: FastAPI + Python 3.13
         pandas, numpy
         scikit-learn (AutoML)
         reportlab (PDF)
         openpyxl
PYTHON LIBRARIES INSTALLED:
fastapi, uvicorn, python-multipart
pandas, numpy, openpyxl
scikit-learn
reportlab
(PyCaret NOT compatible with Python 3.13)
BACKEND SERVICES:
1. cleaner.py
   - detect_problems(df)
   - auto_clean(df) → returns df, report
   - calculate_quality_score(df)
   - detect_problem_type(df)
   - make_readable_name(col_name)
2. analyzer.py
   - generate_statistics(df)
   - generate_insights(df, stats,
     problem_type, readable_columns=None)
3. automl.py
   - run_automl(df, problem_type, target_col)
   - run_classification(df, target_col, results)
   - run_regression(df, target_col, results)
   - run_clustering(df, results)
   Uses scikit-learn NOT PyCaret
   (PyCaret incompatible with Python 3.13)
4. reporter.py (just built)
   - generate_pdf_report(data)
   Uses reportlab
MAIN API ENDPOINTS:
GET  /         → project info
GET  /health   → health check
POST /upload   → main analysis endpoint
POST /generate-report → PDF download
UPLOAD ENDPOINT FLOW:
1. Read file (CSV/Excel) into memory
2. calculate_quality_score (before)
3. detect_problems
4. auto_clean → cleaning_report
5. calculate_quality_score (after)
6. detect_problem_type
7. make_readable_name for all columns
8. generate_statistics
9. generate_insights
10. Prepare chart_data
11. run_automl
12. Return result dict
13. Nothing saved (stateless) ✅
RESULT DICT STRUCTURE:
{
  filename, rows, columns,
  readable_columns,
  problem_detection,
  column_names,
  statistics,
  automl_results,
  insights,
  preview,
  quality_before,
  quality_after,
  problems_found,
  chart_data,
  cleaning_report
}
FRONTEND COMPONENTS ORDER IN App.jsx:
1. FileUpload
2. QualityScore
3. CleaningReport
4. ProblemType
5. MLResults
6. Insights
7. Statistics
8. Charts
9. Summary Cards (rows/cols/quality)
10. Columns Detected
11. Data Preview Table
12. Download PDF button
13. Upload Another File button
CORS ALLOWED ORIGINS:
http://localhost:5173
http://localhost:5174
KNOWN ISSUES/LIMITATIONS:
- PyCaret not compatible with Python 3.13
  Using scikit-learn instead
- Fully joined column names (suicidecount)
  not perfectly split (acceptable for MVP)
- Time series AutoML not implemented yet
- Burmese OCR not implemented yet (future)
AUTOML MODELS USED:
Classification:
  RandomForestClassifier
  LogisticRegression
  DecisionTreeClassifier
  GradientBoostingClassifier
Regression:
  RandomForestRegressor
  LinearRegression
  Ridge
Clustering:
  KMeans (3 clusters)
FEATURE IMPORTANCE:
Uses feature_importances_ for tree models
Uses coef_ for LogisticRegression
CHART TYPES:
Numeric columns → histogram (plotly)
Categorical columns → bar chart (plotly)
Using plotly.js-dist-min directly
NOT react-plotly.js (caused issues)
CAPSTONE PROGRESS:
✅ Capstone 1: Foundation
✅ Capstone 2: Data Pipeline
✅ Capstone 3: AutoML Engine
🔨 Capstone 4: Charts + PDF (in progress)
⏳ Capstone 5: Insights Engine
⏳ Capstone 6: Chat with Data (LLM)
⏳ Capstone 7: PDF Report
⏳ Capstone 8: Deployment
⏳ Capstone 9: Real Users
⏳ Capstone 10: Portfolio Ready
⏳ Capstone 11: OCR Foundation
FUTURE PHASES:
Phase 3: Paper document scanner
Phase 4: Custom Burmese handwriting OCR
         (CRNN/TrOCR - unsolved research gap)
Phase 5: Transfer Learning
Phase 6: Federated Learning
Phase 7: Myanmar language output
Phase 8: Agentic AI layer
HOW TO RUN:
Backend:
cd backend
source venv/bin/activate
uvicorn main:app --reload
Frontend:
cd frontend
npm run dev
HOW TO PUSH TO GITHUB:
git add .
git commit -m "message"
git push origin main
IMPORTANT NOTES:
- Developer has limited web experience
- Learning while building
- Explain concepts before code always
- One thing at a time
- Understanding over speed
- Come back to this chat for guidance
- Code review every 2 weeks
- Confidence level currently: 3/10
  (but actually building 7/10 quality)

Show less


