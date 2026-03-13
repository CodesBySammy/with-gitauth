import joblib
import pandas as pd
import numpy as np
import shap
import threading
from core.config import settings
from core.logger import logger

class XAIExplainer:
    """SHAP-based deployment risk analyzer with lazy model loading."""

    def __init__(self):
        self.model = None
        self.explainer = None
        self._lock = threading.Lock()
        self._loaded = False

    def _ensure_loaded(self):
        """Thread-safe lazy loading — model loads on first analysis, not at import."""
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            try:
                self.model = joblib.load(settings.MODEL_PATH)
                self.explainer = shap.TreeExplainer(self.model)
                logger.info("XAI Engine & SHAP loaded successfully.")
            except Exception as e:
                logger.warning(f"XAI Engine unavailable (Train model first): {e}")
                self.model = None
            self._loaded = True

    def analyze_risk(self, la: int, ld: int, nf: int) -> tuple:
        self._ensure_loaded()
        if not self.model:
            return 0.0, "⚠️ ML Model missing. Run `python pipelines/train_rf_model.py`."

        df = pd.DataFrame([{"la": la, "ld": ld, "nf": nf}])
        
        # Get probability of risk (Class 1)
        risk_prob = self.model.predict_proba(df)[0][1] * 100
        
        # SHAP Values
        shap_values = self.explainer.shap_values(df)
        
        # Safely handle different SHAP library versions
        if isinstance(shap_values, list):
            sv = shap_values[1][0]  # Older SHAP: List format
        elif len(np.array(shap_values).shape) == 3:
            sv = shap_values[0, :, 1]  # Newer SHAP: 3D Array format
        else:
            sv = shap_values[0]  # Fallback

        report = f"### 🧠 Deployment Risk Analysis\n"
        
        # Add a nice badge based on the risk
        if risk_prob < 40:
            report += f"![Low Risk](https://img.shields.io/badge/Risk_Score-{risk_prob:.1f}%25-brightgreen)\n\n"
        elif risk_prob < 75:
            report += f"![Medium Risk](https://img.shields.io/badge/Risk_Score-{risk_prob:.1f}%25-yellow)\n\n"
        else:
            report += f"![High Risk](https://img.shields.io/badge/Risk_Score-{risk_prob:.1f}%25-red)\n\n"

        report += "**Explainable AI Breakdown** (How the model calculated this risk):\n\n"
        report += "| Feature Architectured | Impact on Risk | Delta |\n"
        report += "|-----------------------|----------------|-------|\n"
        
        features = ["Lines Added", "Lines Deleted", "Files Changed"]
        for i, feature in enumerate(features):
            impact = float(sv[i]) * 100
            direction = "🔺 Increased" if impact > 0 else "📉 Decreased"
            report += f"| `{feature}` | {direction} | **{abs(impact):.2f}%** |\n"

        return risk_prob, report

xai_engine = XAIExplainer()