from fastapi import FastAPI
from api.routes import router

app = FastAPI(
    title="Loan Underwriting API",
    version="1.0"
)

app.include_router(router)


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "loan-underwriting-api"
    }
@app.get("/")
def root():
    return {
        "message": "Loan Underwriting API is running",
        "docs": "/docs",
        "health": "/health"
    }