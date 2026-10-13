import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "model_loaded" in data

def test_predict_spam():
    payload = {
        "text": "CONGRATULATIONS! You won a $1000 gift card! Click here now to claim your prize.",
        "source_url": "https://example.com"
    }
    response = client.post("/api/v1/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["prediction"] in ["spam", "ham"]
    assert "confidence" in data
    assert "risk_level" in data
    assert isinstance(data["trigger_words"], list)

def test_predict_ham():
    payload = {
        "text": "Hey, are we still meeting for lunch at 1pm today?",
        "source_url": "https://example.com"
    }
    response = client.post("/api/v1/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["prediction"] == "ham"
    assert data["is_spam"] is False
    assert data["risk_level"] in ["LOW", "MEDIUM"]

def test_feedback():
    payload = {
        "text": "Call me later",
        "predicted": "spam",
        "actual": "ham",
        "user_note": "False positive"
    }
    response = client.post("/api/v1/feedback", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

def test_stats():
    response = client.get("/api/v1/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_predictions" in data
    assert "total_spam" in data
