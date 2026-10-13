# 🛡️ Smart Guard - Gmail AI Spam & Phishing Detection Chrome Extension

An intermediate-level, production-grade security system combining a **Chrome Extension (Manifest V3)** specially built for **Gmail** (`https://mail.google.com/*`) with a **Python FastAPI Machine Learning Microservice**.

![Smart Guard Overview](https://img.shields.shields.io/badge/Manifest-V3-blue?style=flat-square)
![Target](https://img.shields.shields.io/badge/Target-Gmail-red?style=flat-square)
![Backend](https://img.shields.shields.io/badge/Backend-FastAPI-green?style=flat-square)
![ML](https://img.shields.shields.io/badge/ML-Scikit--Learn-orange?style=flat-square)

---

## 🌟 Key Features

* **Chrome Extension (Manifest V3 - Gmail Exclusivity)**:
  * 📧 **Automatic Gmail Opened Email Scanning**: Automatically reads opened email subjects and body text as soon as you open an email in Gmail.
  * 🏷️ **Inline Gmail Security Banners**: Injects a clean security header right above emails (`🚨 SPAM DETECTED` or `🛡️ LEGITIMATE EMAIL`).
  * 🔤 **Scam Term Highlighting**: Highlights suspicious trigger words (`claim`, `free`, `winner`, `urgent`, `gift card`) directly inside email body text.
  * 🔍 **Right-Click Context Menu**: Select any email snippet -> Right-click -> **"Scan selection with Smart Guard"**.
  * 📊 **Glassmorphism Popup Dashboard**: Modern dark-mode popup displaying live stats, risk meter, manual checker, scan history, and customizable sensitivity settings.


* **Python FastAPI Microservice**:
  * 🚀 **High Performance REST API**: Async endpoints (`/api/v1/predict`, `/api/v1/feedback`, `/api/v1/health`, `/api/v1/stats`).
  * 💡 **Explainable AI (XAI)**: Extracts and ranks top suspicious trigger terms from TF-IDF feature weights.
  * 💾 **Local SQLite Logging**: Records scan history and stores user feedback (`feedback.db`) for future model retraining.

---

## 📁 Repository Structure

```text
spam_filtering_system/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI REST server
│   │   ├── classifier.py        # ML inference & explainability engine
│   │   ├── schemas.py           # Pydantic data validation schemas
│   │   └── database.py          # SQLite database logger
│   ├── tests/
│   │   └── test_api.py          # Pytest suite for API endpoints
│   └── requirements.txt         # Backend dependencies
│
├── extension/
│   ├── manifest.json            # Manifest V3 extension configuration
│   ├── background/
│   │   └── service_worker.js    # Background event worker & context menu
│   ├── content/
│   │   ├── content_script.js    # DOM observer & badge injection
│   │   └── styles.css           # Injected toast & highlight styles
│   ├── popup/
│   │   ├── popup.html           # Dashboard UI
│   │   ├── popup.css            # Dark glassmorphism styles
│   │   └── popup.js             # Dashboard interaction & storage manager
│   └── assets/
│       ├── create_icons.py      # Icon generator script
│       ├── icon16.png
│       ├── icon48.png
│       └── icon128.png
│
├── data/                        # Cleaned dataset & modern text data
├── models/                      # Saved joblib ML models & feature weights
├── reports/                     # Model comparison & confusion matrix
├── train_model.py               # ML model training pipeline
└── README.md                    # Project documentation
```

---

## 🚀 Getting Started

### 1. Setup Python Environment & Train Model

```bash
# Install dependencies
pip install -r backend/requirements.txt -r requirements.txt

# Train machine learning model
python train_model.py
```

### 2. Start the FastAPI Microservice

```bash
# Run backend API server on port 8000
uvicorn backend.app.main:app --reload --port 8000
```
> The API documentation will be available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### 3. Load Chrome Extension in Developer Mode

1. Open **Google Chrome** and navigate to `chrome://extensions/`.
2. Enable **Developer mode** in the top right corner.
3. Click **Load unpacked**.
4. Select the `extension/` folder inside this directory:
   `c:/Users/DIVY DEV JAISWAL/Downloads/spam_filtering_system/spam_filtering_system/extension`
5. Pin **Smart Guard** to your Chrome toolbar!

---

## 🧪 Testing the Extension

1. **Context Menu Test**:
   * Highlight text on any website (e.g., *"CONGRATULATIONS! You won a $1000 prize card! Click here now to claim."*).
   * Right-click and choose **"🛡️ Scan selection with Smart Guard"**.
   * A Chrome notification will display the threat score.

2. **Popup Dashboard Test**:
   * Click the Smart Guard icon in your browser toolbar.
   * Paste any message into the **Analyzer** tab and click **Scan Content**.
   * View the **Risk Level**, **Confidence Meter**, and **Trigger Terms**.

3. **Automated Unit Tests**:
   ```bash
   python -m pytest backend/tests/test_api.py
   ```
