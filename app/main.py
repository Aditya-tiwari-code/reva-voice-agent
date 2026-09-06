from fastapi import FastAPI
from app.config import settings

app = FastAPI(
    title="REVA - Real Estate Voice Agent",
    description="Cost-Aware Multilingual AI Voice Agent for Real Estate Lead Qualification",
    version="1.0.0",
)

@app.get("/")
async def root():
    return {
        "message": "Welcome to REVA - Cost-Aware Multilingual AI Voice Agent API",
        "status": "online",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database_url": settings.DATABASE_URL
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
