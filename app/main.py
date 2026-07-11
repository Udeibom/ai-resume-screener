import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.endpoints import router as api_router

app = FastAPI(
    title="Production AI Resume Screening Platform",
    description="Automated semantic ingestion and ranking pipeline powered by FastAPI, pgvector, and LLMs.",
    version="1.0.0",
)

# Configure CORS Middleware for future frontend dashboard integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*"
    ],  # Restrict this to specific origins in a true staging environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the functional routes
app.include_router(api_router, prefix="/api/v1")

# Mount static files for the frontend dashboard
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def read_index():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "message": "Welcome to AI Resume Screener API. Frontend static index.html not found."
    }


@app.get("/health", tags=["System Maintenance"])
async def health_check():
    """
    Superficial health check endpoint for monitoring systems or container load-balancers.
    """
    return {"status": "healthy", "service": "resume-screener-api"}


if __name__ == "__main__":
    # Convenience launch config when running the python file directly
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
