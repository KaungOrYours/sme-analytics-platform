
from dotenv import load_dotenv
load_dotenv()
from services.analyzer import generate_statistics, generate_insights
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from services.automl import run_automl
from services.cleaner import detect_problems, auto_clean, calculate_quality_score, detect_problem_type, make_readable_name
from groq import Groq
import pandas as pd
import io
import os

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

    # Run AutoML
    automl_results = run_automl(
        df_clean,
        problem_detection["problem_type"],
        problem_detection["suggested_target"]
    )

    # Build response
    result = {
        "filename": file.filename,
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

@app.post("/explain")
async def explain_data(request: dict):
    """
    Use Groq LLM to explain analysis results
    in plain English for SME owners
    """
    try:
        client = Groq(
            api_key=os.environ.get("GROQ_API_KEY")
)

        # Build context from analysis data
        context = f"""
        Dataset: {request.get('filename', 'Unknown')}
        Rows: {request.get('rows', 0)}
        Columns: {request.get('columns', 0)}
        Quality Score: {request.get('quality_after', 0)}%
        Problem Type: {request.get('problem_detection', {}).get('problem_type', 'unknown')}
        ML Model: {request.get('automl_results', {}).get('model_name', 'None')}
        ML Performance: {request.get('automl_results', {}).get('performance', {})}
        Key Insights: {request.get('insights', [])}
        """

        user_question = request.get(
            'question',
            'Explain this business data analysis in simple terms for a small business owner. What are the key takeaways and what actions should they consider?'
        )

        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {
                    "role": "system",
                    "content": """You are a friendly business analyst 
                    helping Myanmar small business owners understand 
                    their data. Explain insights in simple plain English. 
                    No technical jargon. Be concise and actionable. 
                    Maximum 3-4 sentences per point."""
                },
                {
                    "role": "user",
                    "content": f"""
                    Here is the analysis of a business dataset:
                    {context}
                    
                    Question: {user_question}
                    """
                }
            ],
            max_tokens=500,
            temperature=0.7
        )

        return {
            "explanation": response.choices[0].message.content,
            "status": "success"
        }

    except Exception as e:
        return {
            "explanation": "Could not generate explanation.",
            "status": "error",
            "error": str(e)
        }