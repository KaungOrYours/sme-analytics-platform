
from dotenv import load_dotenv
load_dotenv()
from services.analyzer import generate_statistics, generate_insights
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from security import (
    SecurityHeadersMiddleware,
    SlidingWindowRateLimiter,
    assert_archive_within_limits,
    assert_frame_within_limits,
    read_upload_limited,
    resolve_file_kind,
    safe_display_filename,
)
from services.automl import run_automl
from services.cleaner import detect_problems, auto_clean, calculate_quality_score, quality_score_breakdown, detect_problem_type, make_readable_name, text_columns
import pandas as pd
import io
import zipfile

app = FastAPI()

# Upload-path controls live in security.py; see its module docstring for the
# threat model each one addresses and for what is deliberately out of scope.
rate_limiter = SlidingWindowRateLimiter()
app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "https://sme-analytics-platform.vercel.app"
    ],
    # Narrowed from allow_methods/allow_headers=["*"] and
    # allow_credentials=True. The API is stateless and uses no cookies or
    # Authorization header, so credentialed cross-origin requests are not
    # needed, and permitting them alongside wildcards is needlessly broad.
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
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
async def upload_file(request: Request, file: UploadFile = File(...)):
    """Analyse one uploaded spreadsheet.

    The order of the checks below is deliberate and is the cheap-before-
    expensive principle: rate limit first (costs nothing), then bound the bytes
    accepted, then establish the real format, then bound the decompressed and
    parsed size, and only then run the ML pipeline. Every rejection happens
    before the work it would otherwise pay for.
    """
    rate_limiter.check(request)

    contents = await read_upload_limited(file)
    if not contents:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty."
        )

    kind = resolve_file_kind(contents, file.filename)

    if kind == "csv":
        try:
            df = pd.read_csv(io.BytesIO(contents))
        except (pd.errors.ParserError, pd.errors.EmptyDataError,
                UnicodeDecodeError, ValueError) as e:
            raise HTTPException(
                status_code=400,
                detail=f"Could not read this CSV file: {str(e)[:150]}"
            )
    else:
        # Measure the archive's declared expansion before openpyxl performs it.
        assert_archive_within_limits(contents)
        try:
            df = pd.read_excel(io.BytesIO(contents))
        except (ValueError, KeyError, zipfile.BadZipFile) as e:
            # openpyxl raises more than ValueError on a malformed workbook;
            # catching only ValueError previously sent those to the generic
            # 500 handler, reporting a server fault for a bad client file.
            raise HTTPException(
                status_code=400,
                detail=f"Could not read this Excel file: {str(e)[:150]}"
            )

    if df.empty or len(df.columns) == 0:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file has no data to analyze."
        )

    assert_frame_within_limits(df)

    try:
        return _analyze(df, safe_display_filename(file.filename))
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

    # Calculate quality after cleaning. The breakdown is kept alongside the
    # scalar so the response can show which dimension drove the score rather
    # than only the composite -- the score is a project heuristic, not a
    # validated metric (see quality_score_breakdown's docstring).
    quality_after_detail = quality_score_breakdown(df_clean)
    quality_after = quality_after_detail["score"]

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

    # text_columns, not select_dtypes(include=['object']): the latter only
    # matches pandas 3 string columns through a deprecated path scheduled for
    # removal (see cleaner._is_text_dtype).
    for col in text_columns(df_clean)[:2]:
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
        "quality_breakdown": quality_after_detail,
        "problems_found": problems,
        "chart_data": chart_data,
        "cleaning_report": cleaning_report
    }

    return result
