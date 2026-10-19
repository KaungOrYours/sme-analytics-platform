
from dotenv import load_dotenv
load_dotenv()
from services.analyzer import generate_statistics, generate_insights
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from services.automl import run_automl
from services.cleaner import detect_problems, auto_clean, calculate_quality_score, detect_problem_type, make_readable_name
import pandas as pd
import io

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10MB, matches the frontend's own check

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "https://sme-analytics-platform.vercel.app"
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

    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail="File exceeds the 10MB limit. Please reduce the file size and try again."
        )

    # Read with pandas
    if file.filename.endswith('.csv'):
        try:
            df = pd.read_csv(io.BytesIO(contents))
        except (pd.errors.ParserError, UnicodeDecodeError, ValueError) as e:
            raise HTTPException(
                status_code=400,
                detail=f"Could not read this CSV file: {str(e)[:150]}"
            )
    elif file.filename.endswith(('.xlsx', '.xls')):
        try:
            df = pd.read_excel(io.BytesIO(contents))
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Could not read this Excel file: {str(e)[:150]}"
            )
    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Please upload a CSV or Excel file (.csv, .xlsx, .xls)."
        )

    if df.empty or len(df.columns) == 0:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file has no data to analyze."
        )

    try:
        return _analyze(df, file.filename)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Something went wrong while analyzing this file: {str(e)[:150]}"
        )


def _analyze(df, filename):
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

    # Create readable column names
    readable_columns = {
        col: make_readable_name(col)
        for col in df_clean.columns
    }

    # Generate statistics
    statistics = generate_statistics(df_clean)

    # Generate insights
    insights = generate_insights(
        df_clean,
        statistics,
        problem_detection["problem_type"],
        readable_columns
    )

    # Prepare chart data
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

    # Correlation heatmap across numeric columns, so the "key driver"
    # insight from generate_insights has a chart to back it up
    numeric_df = df_clean.select_dtypes(include=['number'])
    if len(numeric_df.columns) >= 2:
        corr = numeric_df.corr().round(3)
        chart_data["_correlation"] = {
            "type": "correlation",
            "columns": [
                readable_columns.get(c, c) for c in corr.columns
            ],
            "matrix": corr.values.tolist()
        }

    # Run AutoML
    automl_results = run_automl(
        df_clean,
        problem_detection["problem_type"],
        problem_detection["suggested_target"]
    )

    # Build response
    result = {
        "filename": filename,
        "rows": len(df_clean),
        "columns": len(df_clean.columns),
        "readable_columns": readable_columns,
        "problem_detection": problem_detection,
        "column_names": list(df_clean.columns),
        "statistics": statistics,
        "automl_results": automl_results,
        "insights": insights,
        "preview": df_clean.head(5).to_dict(orient='records'),
        "quality_before": quality_before,
        "quality_after": quality_after,
        "problems_found": problems,
        "chart_data": chart_data,
        "cleaning_report": cleaning_report
    }

    return result
