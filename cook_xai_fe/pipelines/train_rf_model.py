import os
import sys
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# Ensure core module is found when running as script
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings
from core.logger import logger

def train_and_save_model():
    os.makedirs(settings.MODELS_DIR, exist_ok=True)
    
    # 1. Load the REAL Apache JIT Dataset
    dataset_path = os.path.join(os.path.dirname(__file__), "apachejit_train.csv")
    
    if not os.path.exists(dataset_path):
        logger.error(f"❌ Could not find {dataset_path}. Please make sure the CSV is in the pipelines folder!")
        return

    logger.info(f"📊 Loading real dataset from {dataset_path}...")
    df = pd.read_csv(dataset_path)

    # 2. Extract Features and Target Label
    target_column = "buggy" 
    
    # Convert the boolean True/False into 1/0 for the ML model and SHAP Explainer
    df[target_column] = df[target_column].astype(int)

    # We use la, ld, nf because these are the exact metrics our orchestrator extracts from GitHub
    X = df[["la", "ld", "nf"]]
    y = df[target_column]

    # Split the data into 80% training and 20% testing
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 3. Train the Model
    logger.info("🧠 Training Random Forest Defect Predictor on Apache data...")
    # max_depth limits how complex the trees get, preventing overfitting
    model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    model.fit(X_train, y_train)
    
    # 4. Evaluate and Log Accuracy
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    logger.info(f"🎯 Model Accuracy: {accuracy * 100:.2f}%")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))

    # 5. Save the Model
    joblib.dump(model, settings.MODEL_PATH)
    logger.info(f"✅ Real Apache model successfully saved to {settings.MODEL_PATH}")

if __name__ == "__main__":
    train_and_save_model()