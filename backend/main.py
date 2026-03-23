from fastapi import FastAPI

# Create FastAPI app
app = FastAPI()

# First endpoint
@app.get("/")
def home():
    return {
        "project": "SME Analytics Platform",
        "version": "1.0",
        "description": "Upload your Excel, get instant business insights",
        "status": "running"
    }

# Health check endpoint
@app.get("/health")
def health():
    return {
        "status": "healthy",
        "message": "System is running perfectly"
    }
