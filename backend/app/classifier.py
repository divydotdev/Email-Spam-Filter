import re
from pathlib import Path
from datetime import datetime, timezone
import joblib

MODEL_PATH = Path(__file__).resolve().parent.parent.parent / "models" / "spam_model.joblib"
WEIGHTS_PATH = Path(__file__).resolve().parent.parent.parent / "models" / "feature_weights.joblib"

# High-confidence scam & phishing keywords (excluding innocent words like 'click', 'account', 'link')
DEFAULT_SPAM_KEYWORDS = {
    "lottery", "jackpot", "unclaimed", "winner", "winning", "prize", "sweepstakes",
    "pre-approved", "0% interest", "wire transfer", "inheritance", "bitcoin", "crypto",
    "payday loan", "instant cash", "unauthorized charge", "suspend within 24", "deactivate in 24",
    "kyc verification", "aadhaar", "pan card", "guaranteed returns", "roi guaranteed", "geek squad"
}

# Neutral / innocent common words in genuine business and newsletter emails
NEUTRAL_TERMS = {
    "the", "and", "for", "with", "from", "that", "this", "new", "get", "will", "your",
    "have", "you", "about", "all", "are", "but", "can", "has", "her", "his", "how",
    "its", "may", "more", "not", "now", "one", "our", "out", "see", "some", "than",
    "their", "them", "then", "there", "these", "they", "time", "use", "was", "way",
    "what", "when", "which", "who", "why", "would", "daily", "brief", "today", "yesterday",
    "weekly", "newsletter", "subscription", "settings", "manage", "team", "project",
    "report", "companies", "market", "discuss", "view", "read", "update", "meeting", "invoice", "receipt"
}


class SpamClassifier:
    def __init__(self):
        self.model = None
        self.feature_weights = {}
        self.is_loaded = False
        self.load_model()

    def load_model(self):
        if MODEL_PATH.exists():
            try:
                self.model = joblib.load(MODEL_PATH)
                self.is_loaded = True
                print(f"Loaded ML Model from {MODEL_PATH}")
            except Exception as e:
                print(f"Failed to load model: {e}")
                self.is_loaded = False

        if WEIGHTS_PATH.exists():
            try:
                self.feature_weights = joblib.load(WEIGHTS_PATH)
                print(f"Loaded Feature Weights ({len(self.feature_weights)} terms)")
            except Exception as e:
                print(f"Failed to load feature weights: {e}")
                self.feature_weights = {}

    def extract_trigger_words(self, text: str, max_words: int = 5) -> list[str]:
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words)-1)]
        all_terms = words + bigrams

        scored_terms = []
        for term in set(all_terms):
            if term in NEUTRAL_TERMS:
                continue
            if term in self.feature_weights:
                weight = self.feature_weights[term]
                # High threshold so only unequivocally spammy words are flagged
                if weight > 1.2:
                    scored_terms.append((term, weight))
            elif term in DEFAULT_SPAM_KEYWORDS:
                scored_terms.append((term, 2.0))

        # Sort by weight descending
        scored_terms.sort(key=lambda x: x[1], reverse=True)
        return [t[0] for t in scored_terms[:max_words]]

    def predict(self, text: str, threshold: float = 0.65) -> dict:
        now_iso = datetime.now(timezone.utc).isoformat()
        cleaned_text = text.strip()

        if not cleaned_text:
            return {
                "prediction": "ham",
                "is_spam": False,
                "confidence": 100.0,
                "risk_level": "LOW",
                "trigger_words": [],
                "timestamp": now_iso
            }

        if not self.is_loaded or self.model is None:
            triggers = self.extract_trigger_words(cleaned_text)
            is_spam = len(triggers) >= 2
            return {
                "prediction": "spam" if is_spam else "ham",
                "is_spam": is_spam,
                "confidence": 80.0 if is_spam else 90.0,
                "risk_level": "HIGH" if is_spam else "LOW",
                "trigger_words": triggers if is_spam else [],
                "timestamp": now_iso
            }

        probabilities = self.model.predict_proba([cleaned_text])[0]
        # index 1 is spam probability
        spam_prob = float(probabilities[1])
        is_spam = bool(spam_prob >= threshold)
        confidence = float(max(probabilities)) * 100.0

        if is_spam:
            trigger_words = self.extract_trigger_words(cleaned_text)
            if confidence >= 85.0:
                risk_level = "CRITICAL"
            elif confidence >= 70.0:
                risk_level = "HIGH"
            else:
                risk_level = "MEDIUM"
        else:
            # Genuine email / ham: no suspicious triggers attached
            trigger_words = []
            risk_level = "LOW"

        return {
            "prediction": "spam" if is_spam else "ham",
            "is_spam": is_spam,
            "confidence": round(confidence, 2),
            "risk_level": risk_level,
            "trigger_words": trigger_words,
            "timestamp": now_iso
        }


classifier_service = SpamClassifier()
