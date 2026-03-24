from services.analyzer import generate_statistics, generate_insights
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from services.cleaner import detect_problems, auto_clean, calculate_quality_score, detect_problem_type
import pandas as pd
import io

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:5173",
    "http://localhost:5174"
],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {
        "project": "SME Analytics Platform",
        "version": "1.0",
        "description": "Upload your Excel, get instant business insights",
        "status": "running"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "message": "System is running perfectly"
    }

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):

    # Read file into memory
    contents = await file.read()

    # Read with pandas
    if file.filename.endswith('.csv'):
        df = pd.read_csv(io.BytesIO(contents))
    elif file.filename.endswith(('.xlsx', '.xls')):
        df = pd.read_excel(io.BytesIO(contents))
    else:
        return {"error": "Unsupported file type"}

    # Calculate quality before cleaning
    quality_before = calculate_quality_score(df)

    # Detect problems
    problems = detect_problems(df)

    # Auto clean
    df_clean, cleaning_report = auto_clean(df)

    # Calculate quality after cleaning
    quality_after = calculate_quality_score(df_clean)

    # Detect problem type
    problem_detection = detect_problem_type(df_clean)

    # Generate statistics
    statistics = generate_statistics(df_clean)

    # Generate insights
    insights = generate_insights(
        df_clean,
        statistics,
        problem_detection["problem_type"]
    )

    # Prepare chart data ← MOVED UP HERE
    chart_data = {}

    for col in df_clean.select_dtypes(
        include=['number']
    ).columns[:4]:
        chart_data[col] = {
            "type": "numeric",
            "values": df_clean[col].dropna().tolist()[:500]
        }

    for col in df_clean.select_dtypes(
        include=['object']
    ).columns[:2]:
        counts = df_clean[col].value_counts().head(8)
        chart_data[col] = {
            "type": "categorical",
            "labels": counts.index.tolist(),
            "values": counts.values.tolist()
        }

    # Build response ← AFTER chart_data
    result = {
        "filename": file.filename,
        "rows": len(df_clean),
        "columns": len(df_clean.columns),
        "problem_detection": problem_detection,
        "column_names": list(df_clean.columns),
        "statistics": statistics,
        "insights": insights,
        "preview": df_clean.head(5).to_dict(orient='records'),
        "quality_before": quality_before,
        "quality_after": quality_after,
        "problems_found": problems,
        "chart_data": chart_data,
        "cleaning_report": cleaning_report
    }

    return result