from fastapi import FastAPI
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(
    title="Enterprise Planning Intelligence Agent",
    description="Agentic AI system for enterprise planning, cross-system orchestration, and Epic sizing.",
    version="0.1.0",
)

@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "0.1.0",
        "anthropic_key_loaded": bool(os.environ.get("ANTHROPIC_API_KEY")),
    }
