from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.app.schemas import (
    PredictRequest, PredictResponse,
    FeedbackRequest, FeedbackResponse,
    HealthResponse, StatsResponse
)
from backend.app.classifier import classifier_service
from backend.app.database import init_db, log_prediction, save_feedback, get_stats

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="Smart Guard Spam Detection API",
    description="Backend microservice for Chrome Extension real-time spam and phishing detection.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for Chrome Extensions and local hosts
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




@app.get("/", response_model=HealthResponse)
@app.get("/api/v1/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(
        status="online",
        model_loaded=classifier_service.is_loaded,
        version="1.0.0"
    )


@app.post("/api/v1/predict", response_model=PredictResponse)
def predict_spam(request: PredictRequest):
    try:
        result = classifier_service.predict(request.text, threshold=request.threshold or 0.5)
        log_prediction(
            text=request.text,
            source_url=request.source_url,
            prediction=result["prediction"],
            confidence=result["confidence"],
            risk_level=result["risk_level"]
        )
        return PredictResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@app.post("/api/v1/feedback", response_model=FeedbackResponse)
def report_feedback(request: FeedbackRequest):
    try:
        save_feedback(
            text=request.text,
            predicted=request.predicted,
            actual=request.actual,
            user_note=request.user_note
        )
        return FeedbackResponse(
            status="success",
            message="Thank you! Feedback saved for future model retraining."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Feedback save error: {str(e)}")


@app.get("/api/v1/stats", response_model=StatsResponse)
def fetch_stats():
    stats = get_stats()
    return StatsResponse(**stats)
