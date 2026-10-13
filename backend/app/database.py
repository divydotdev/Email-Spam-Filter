import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

DB_PATH = Path(__file__).resolve().parent.parent / "feedback.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scan_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            source_url TEXT,
            prediction TEXT NOT NULL,
            confidence REAL NOT NULL,
            risk_level TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            predicted TEXT NOT NULL,
            actual TEXT NOT NULL,
            user_note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()


def log_prediction(text: str, source_url: str | None, prediction: str, confidence: float, risk_level: str):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO scan_logs (text, source_url, prediction, confidence, risk_level) VALUES (?, ?, ?, ?, ?)",
            (text, source_url or "", prediction, confidence, risk_level)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database log error: {e}")


def save_feedback(text: str, predicted: str, actual: str, user_note: str | None):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO feedback_reports (text, predicted, actual, user_note) VALUES (?, ?, ?, ?)",
            (text, predicted, actual, user_note or "")
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database feedback save error: {e}")


def get_stats() -> Dict[str, int]:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM scan_logs")
        total_predictions = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM scan_logs WHERE prediction = 'spam'")
        total_spam = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM scan_logs WHERE prediction = 'ham'")
        total_ham = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM feedback_reports")
        total_feedback = cursor.fetchone()[0]
        
        conn.close()
        return {
            "total_predictions": total_predictions,
            "total_spam": total_spam,
            "total_ham": total_ham,
            "total_feedback_reports": total_feedback
        }
    except Exception as e:
        print(f"Database get_stats error: {e}")
        return {
            "total_predictions": 0,
            "total_spam": 0,
            "total_ham": 0,
            "total_feedback_reports": 0
        }
