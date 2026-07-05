import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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


@app.get("/health", tags=["System Maintenance"])
async def health_check():
    """
    Superficial health check endpoint for monitoring systems or container load-balancers.
    """
    return {"status": "healthy", "service": "resume-screener-api"}


if __name__ == "__main__":
    # Convenience launch config when running the python file directly
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
