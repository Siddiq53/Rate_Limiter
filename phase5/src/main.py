from fastapi import FastAPI, Request, Response, HTTPException, Depends
from src.limiters.fixed_window import FixedWindowRateLimiter

app = FastAPI(
    title="Rate Limiter Lab",
    description="An educational lab to learn and compare rate limiting algorithms.",
    version="0.1.0"
)

# Initialize the fixed window rate limiter: 10 requests per 60 seconds
limiter = FixedWindowRateLimiter(limit=10, window=60)

async def rate_limit(request: Request, response: Response):
    """
    FastAPI dependency that enforces rate limiting based on client IP.
    Appends rate limit status headers to the response.
    """
    client_ip = request.client.host if request.client else "unknown"
    is_allowed, remaining, reset_at = limiter.check_rate_limit(client_ip)
    
    # Set headers on the successful response
    response.headers["X-RateLimit-Limit"] = str(limiter.limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(reset_at)
    
    if not is_allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again later.",
            headers={
                "X-RateLimit-Limit": str(limiter.limit),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(reset_at)
            }
        )

@app.get("/api/test", dependencies=[Depends(rate_limit)])
async def test_endpoint():
    """
    A simple test endpoint to verify the API server is functional.
    """
    return {
        "status": "ok",
        "message": "Rate Limiter Lab API is running"
    }
