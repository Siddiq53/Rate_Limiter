from fastapi import FastAPI

app = FastAPI(
    title="Rate Limiter Lab",
    description="An educational lab to learn and compare rate limiting algorithms.",
    version="0.1.0"
)

@app.get("/api/test")
async def test_endpoint():
    """
    A simple test endpoint to verify the API server is functional.
    """
    return {
        "status": "ok",
        "message": "Rate Limiter Lab API is running"
    }
