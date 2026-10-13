import io
import re
import zipfile
from pathlib import Path
from urllib.request import urlopen, Request

import joblib
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB, ComplementNB
from sklearn.ensemble import VotingClassifier
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix,
    precision_score, recall_score, f1_score, roc_auc_score
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

DATA_URL = "https://archive.ics.uci.edu/static/public/228/sms+spam+collection.zip"
DATA_DIR = Path("data")
MODEL_DIR = Path("models")
REPORT_DIR = Path("reports")

BASE_CSV_FILE = DATA_DIR / "sms_spam_clean.csv"
SPAM_TXT_FILE = DATA_DIR / "modern_spam.txt"
HAM_TXT_FILE = DATA_DIR / "modern_ham.txt"

DATA_DIR.mkdir(exist_ok=True)
MODEL_DIR.mkdir(exist_ok=True)
REPORT_DIR.mkdir(exist_ok=True)


def parse_text_dataset_file(file_path: Path, default_label: int) -> list[dict]:
    """
    Parses lines from a dataset file. Intelligently supports:
    - Labelled format: 'spam\t<message>' or 'ham\t<message>'
    - Unlabelled format: '<message>' using default_label
    - Ignores comment lines starting with '#' and empty lines.
    """
    if not file_path.exists() or file_path.stat().st_size == 0:
        return []

    records = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            # Check for explicit spam/ham label prefix
            if re.match(r"^spam[\t\s]+", stripped, re.IGNORECASE):
                msg = re.sub(r"^spam[\t\s]+", "", stripped, flags=re.IGNORECASE).strip()
                if msg:
                    records.append({"label": 1, "message": msg})
            elif re.match(r"^ham[\t\s]+", stripped, re.IGNORECASE):
                msg = re.sub(r"^ham[\t\s]+", "", stripped, flags=re.IGNORECASE).strip()
                if msg:
                    records.append({"label": 0, "message": msg})
            else:
                records.append({"label": default_label, "message": stripped})

    return records


def load_dataset() -> pd.DataFrame:
    """Loads datasets from local CSV/text files and auto-initializes base dataset if needed."""
    frames = []

    # 1. Load local base dataset if valid & non-empty
    if BASE_CSV_FILE.exists() and BASE_CSV_FILE.stat().st_size > 50:
        try:
            base_df = pd.read_csv(BASE_CSV_FILE)
            if "label" in base_df.columns and "message" in base_df.columns:
                frames.append(base_df[["label", "message"]])
                print(f"Loaded {len(base_df)} base records from {BASE_CSV_FILE}")
        except Exception as e:
            print(f"Notice: Could not parse existing base CSV ({e}).")

    # 2. If no valid base records, download official UCI dataset once
    if not frames:
        try:
            print("Fetching base SMS Spam collection dataset...")
            req = Request(DATA_URL, headers={"User-Agent": "Mozilla/5.0"})
            zip_bytes = urlopen(req, timeout=15).read()
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
                raw = z.read("SMSSpamCollection").decode("utf-8", errors="ignore")
            rows = [line.split("\t", 1) for line in raw.splitlines() if "\t" in line]
            df_base = pd.DataFrame(rows, columns=["label", "message"])
            df_base["label"] = df_base["label"].map({"ham": 0, "spam": 1})
            frames.append(df_base)
            print(f"Downloaded {len(df_base)} records from UCI SMS Collection.")
        except Exception as e:
            print(f"Notice: Network download skipped ({e}). Using local text datasets.")

    # 3. Parse modern_spam.txt (handles both spam/ham prefixes or plain text)
    spam_records = parse_text_dataset_file(SPAM_TXT_FILE, default_label=1)
    if spam_records:
        frames.append(pd.DataFrame(spam_records))
        print(f"Loaded {len(spam_records)} records from {SPAM_TXT_FILE}")

    # 4. Parse modern_ham.txt (handles both spam/ham prefixes or plain text)
    ham_records = parse_text_dataset_file(HAM_TXT_FILE, default_label=0)
    if ham_records:
        frames.append(pd.DataFrame(ham_records))
        print(f"Loaded {len(ham_records)} records from {HAM_TXT_FILE}")

    if not frames:
        raise FileNotFoundError(
            f"No training data found! Please ensure {SPAM_TXT_FILE} or {HAM_TXT_FILE} exists."
        )

    # 5. Merge, clean, and deduplicate
    combined_df = pd.concat(frames, ignore_index=True)
    combined_df = combined_df.dropna().drop_duplicates(subset=["message"])
    combined_df["label"] = combined_df["label"].astype(int)

    # Cache combined clean dataset locally
    combined_df.to_csv(BASE_CSV_FILE, index=False)

    spam_count = int(sum(combined_df["label"] == 1))
    ham_count = int(sum(combined_df["label"] == 0))
    print(f"Total clean dataset size: {len(combined_df)} samples (Spam: {spam_count}, Ham: {ham_count})")
    return combined_df


def train_and_evaluate():
    print("=" * 60)
    print("STARTING SPAM CLASSIFIER MODEL TRAINING")
    print("=" * 60)

    df = load_dataset()

    X_train, X_test, y_train, y_test = train_test_split(
        df["message"], df["label"], test_size=0.2, random_state=42, stratify=df["label"]
    )

    tfidf_config = {
        "lowercase": True,
        "stop_words": "english",
        "ngram_range": (1, 3),
        "sublinear_tf": True,
        "strip_accents": "unicode",
        "min_df": 1,
        "max_df": 0.95
    }

    models = {
        "LogisticRegression_Balanced": Pipeline([
            ("tfidf", TfidfVectorizer(**tfidf_config)),
            ("classifier", LogisticRegression(class_weight="balanced", C=2.5, max_iter=2000, random_state=42))
        ]),
        "Complement_NaiveBayes": Pipeline([
            ("tfidf", TfidfVectorizer(**tfidf_config)),
            ("classifier", ComplementNB(alpha=0.1))
        ]),
        "Multinomial_NaiveBayes": Pipeline([
            ("tfidf", TfidfVectorizer(**tfidf_config)),
            ("classifier", MultinomialNB(alpha=0.08))
        ]),
        "Ensemble_SoftVoting": Pipeline([
            ("tfidf", TfidfVectorizer(**tfidf_config)),
            ("classifier", VotingClassifier(
                estimators=[
                    ("lr", LogisticRegression(class_weight="balanced", C=2.5, max_iter=2000, random_state=42)),
                    ("cnb", ComplementNB(alpha=0.1)),
                    ("mnb", MultinomialNB(alpha=0.08))
                ],
                voting="soft"
            ))
        ])
    }

    results = []
    best_name, best_model, best_composite_score = None, None, -1

    for name, model in models.items():
        print(f"Training and evaluating {name}...")
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        prob = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else None

        acc = accuracy_score(y_test, pred)
        prec = precision_score(y_test, pred, zero_division=0)
        rec = recall_score(y_test, pred, zero_division=0)
        f1 = f1_score(y_test, pred, zero_division=0)
        roc_auc = roc_auc_score(y_test, prob) if prob is not None else 0.0

        results.append({
            "model": name,
            "accuracy": round(acc, 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
            "roc_auc": round(roc_auc, 4)
        })

        composite_score = (f1 * 0.7) + (rec * 0.3)
        if composite_score > best_composite_score:
            best_composite_score = composite_score
            best_name = name
            best_model = model

    results_df = pd.DataFrame(results)
    print("\n" + "=" * 60)
    print("MODEL BENCHMARK RESULTS")
    print("=" * 60)
    print(results_df.to_string(index=False))

    results_df.to_csv(REPORT_DIR / "model_comparison.csv", index=False)

    # Save best model
    joblib.dump(best_model, MODEL_DIR / "spam_model.joblib")
    print(f"\n[OK] Best model selected: {best_name} (Composite Score: {best_composite_score:.4f})")
    print(f"[OK] Model saved to {MODEL_DIR / 'spam_model.joblib'}")

    # Extract & Save Feature Weights
    try:
        vectorizer = best_model.named_steps["tfidf"]
        classifier = best_model.named_steps["classifier"]
        feature_names = vectorizer.get_feature_names_out()

        if hasattr(classifier, "coef_"):
            weights = classifier.coef_[0]
        elif hasattr(classifier, "feature_log_prob_"):
            weights = classifier.feature_log_prob_[1] - classifier.feature_log_prob_[0]
        elif hasattr(classifier, "estimators_"):
            est_weights = []
            for est in classifier.estimators_:
                if hasattr(est, "coef_"):
                    est_weights.append(est.coef_[0])
                elif hasattr(est, "feature_log_prob_"):
                    est_weights.append(est.feature_log_prob_[1] - est.feature_log_prob_[0])
            weights = sum(est_weights) / len(est_weights) if est_weights else None
        else:
            weights = None

        if weights is not None:
            feature_weight_map = dict(zip(feature_names, [float(w) for w in weights]))
            joblib.dump(feature_weight_map, MODEL_DIR / "feature_weights.joblib")
            print(f"[OK] Saved {len(feature_weight_map)} feature weights to {MODEL_DIR / 'feature_weights.joblib'}")
    except Exception as e:
        print(f"Feature weights extraction notice: {e}")

    # Generate Confusion Matrix Plot
    best_pred = best_model.predict(X_test)
    cm = confusion_matrix(y_test, best_pred)
    plt.figure(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=["Ham (Legitimate)", "Spam"],
                yticklabels=["Ham (Legitimate)", "Spam"])
    plt.xlabel("Predicted Label", fontweight="bold")
    plt.ylabel("Actual Label", fontweight="bold")
    plt.title(f"Confusion Matrix ({best_name})", fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.savefig(REPORT_DIR / "confusion_matrix.png", dpi=200)
    plt.close()
    print(f"[OK] Confusion matrix plot saved to {REPORT_DIR / 'confusion_matrix.png'}")

    # Save Classification Report
    with open(REPORT_DIR / "classification_report.txt", "w", encoding="utf-8") as f:
        f.write(f"BEST PERFORMING MODEL: {best_name}\n")
        f.write("=" * 50 + "\n\n")
        f.write(classification_report(y_test, best_pred, target_names=["Ham", "Spam"], digits=4))
    print(f"[OK] Classification report saved to {REPORT_DIR / 'classification_report.txt'}")

    print("\n" + "=" * 60)
    print("ALL TRAINING & EVALUATION TASKS COMPLETED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    train_and_evaluate()
