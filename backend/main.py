from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from services.cleaner import detect_problems, auto_clean, calculate_quality_score
import pandas as pd
import io

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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

    # Build response
    result = {
        "filename": file.filename,
        "rows": len(df_clean),
        "columns": len(df_clean.columns),
        "column_names": list(df_clean.columns),
        "preview": df_clean.head(5).to_dict(orient="records"),
        "quality_before": quality_before,
        "quality_after": quality_after,
        "problems_found": problems,
        "cleaning_report": cleaning_report
    }

    return result
