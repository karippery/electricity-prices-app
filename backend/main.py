
import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apps.routers import prices
from config import settings

app = FastAPI(
    title="Austrian Electricity Prices API",
    description="API for retrieving day-ahead electricity prices from aWATTar",
    version="1.0.0",
    contact={
        "name": "API Support",
        "email": "support@example.com"
    }
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Include routers
app.include_router(prices.router)

@app.get("/health")
async def health_check():
    """Detailed health check endpoint"""
    return {
        "status": "healthy",
        "service": "Electricity Prices API",
        "version": "1.0.0",
        "docs": "/docs",
        "timezone": str(settings.VIENNA_TZ),
        "timestamp":  datetime.datetime.now(settings.VIENNA_TZ).isoformat(),
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)