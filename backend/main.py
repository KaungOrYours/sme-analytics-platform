from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow frontend to talk to backend
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