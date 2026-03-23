from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
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

    # Read file content into memory
    contents = await file.read()

    # Detect file type and read with pandas
    if file.filename.endswith('.csv'):
        df = pd.read_csv(io.BytesIO(contents))
    elif file.filename.endswith(('.xlsx', '.xls')):
        df = pd.read_excel(io.BytesIO(contents))
    else:
        return {"error": "Unsupported file type"}

    # Extract basic info
    info = {
        "filename": file.filename,
        "rows": len(df),
        "columns": len(df.columns),
        "column_names": list(df.columns),
        "preview": df.head(5).to_dict(orient="records")
    }

    # File deleted from memory automatically
    # Nothing saved to disk ✅
    return info
