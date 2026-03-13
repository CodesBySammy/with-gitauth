from transformers import pipeline
from core.logger import logger
import threading

class NLPCodeBERT:
    """CodeBERT semantic vulnerability scanner with lazy model loading."""

    def __init__(self):
        self.analyzer = None
        self._lock = threading.Lock()
        self._loaded = False

    def _ensure_loaded(self):
        """Thread-safe lazy loading — model loads on first scan, not at import."""
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            logger.info("Loading CodeBERT (May take a moment)...")
            try:
                self.analyzer = pipeline(
                    "text-classification",
                    model="mrm8488/codebert-base-finetuned-detect-insecure-code"
                )
                logger.info("✅ CodeBERT Initialized.")
            except Exception as e:
                logger.error(f"CodeBERT load failed: {e}")
                self.analyzer = None
            self._loaded = True

    def scan(self, raw_code: str, filename: str) -> str:
        self._ensure_loaded()
        if not self.analyzer:
            return ""
        try:
            # Let the pipeline handle proper token truncation rather than string slicing
            prediction = self.analyzer(raw_code, truncation=True, max_length=512)
            label = prediction[0]['label']
            confidence = round(prediction[0]['score'] * 100, 2)
            
            if label in ["VULNERABLE", "LABEL_1"]:
                return f"| `{filename}` | 🔴 Semantic Vuln | {confidence}% |"
            return f"| `{filename}` | 🟢 Secure | {confidence}% |"
        except Exception as e:
            logger.warning(f"CodeBERT scan failed for {filename}: {e}")
            return f"| `{filename}` | ⚠️ Scan Failed | N/A |"

nlp_engine = NLPCodeBERT()