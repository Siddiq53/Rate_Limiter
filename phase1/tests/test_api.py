from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_api_test():
    """
    Test that the /api/test endpoint responds with 200 OK and the expected message.
    """
    response = client.get("/api/test")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "message": "Rate Limiter Lab API is running"
    }
