from typing import List, Optional
from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    text: str = Field(..., description="Message or text content to classify")
    source_url: Optional[str] = Field(None, description="URL where text was captured from")
    threshold: Optional[float] = Field(0.5, ge=0.0, le=1.0, description="Spam decision threshold")


class PredictResponse(BaseModel):
    prediction: str = Field(..., description="Classification result: 'spam' or 'ham'")
    is_spam: bool = Field(..., description="True if spam, False if ham")
    confidence: float = Field(..., description="Model confidence score percentage (0-100)")
    risk_level: str = Field(..., description="Risk category: LOW, MEDIUM, HIGH, CRITICAL")
    trigger_words: List[str] = Field(default_factory=list, description="Top suspicious terms detected")
    timestamp: str = Field(..., description="ISO format UTC timestamp")


class FeedbackRequest(BaseModel):
    text: str = Field(..., description="Text content reported")
    predicted: str = Field(..., description="Model prediction: 'spam' or 'ham'")
    actual: str = Field(..., description="User ground truth label: 'spam' or 'ham'")
    user_note: Optional[str] = Field(None, description="Optional user comments")


class FeedbackResponse(BaseModel):
    status: str
    message: str


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    version: str


class StatsResponse(BaseModel):
    total_predictions: int
    total_spam: int
    total_ham: int
    total_feedback_reports: int
