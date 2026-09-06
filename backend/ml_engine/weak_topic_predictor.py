"""
ml_engine/weak_topic_predictor.py
Random Forest model that predicts which topics a student will struggle with
BEFORE they take the next quiz, based on their Digital Twin history.

At demo stage: uses rule-based fallback (no training data required).
In production: trains on accumulated session history.
"""
import numpy as np
import logging
import os
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    import joblib
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("[WeakTopicPredictor] scikit-learn not installed, using rule-based fallback")


class WeakTopicPredictor:
    """
    Predicts future-risk topics from Digital Twin state.
    Two modes:
      - rule_based:  immediate, no training data needed (demo-ready)
      - ml_model:    Random Forest trained on session history (production)
    """

    def __init__(self):
        self.model      = None
        self.scaler     = None
        self.is_trained = False
        self._model_path = Path(settings.BASE_DIR) / "ml_models" / "weak_topic_rf.joblib"
        self._scaler_path = Path(settings.BASE_DIR) / "ml_models" / "weak_topic_scaler.joblib"
        self._try_load()

    def _try_load(self):
        if SKLEARN_AVAILABLE and self._model_path.exists() and self._scaler_path.exists():
            try:
                self.model      = joblib.load(str(self._model_path))
                self.scaler     = joblib.load(str(self._scaler_path))
                self.is_trained = True
                logger.info("[WeakTopicPredictor] Loaded trained RF model from disk")
            except Exception as e:
                logger.warning(f"[WeakTopicPredictor] Could not load model: {e}")

    def predict_at_risk(self, twin_state: dict, top_n: int = 5) -> list:
        """
        Predict which topics are at risk of failure in the next session.

        Args:
            twin_state: dict with keys from LearnerDigitalTwin:
              - verified_mastery: {topic_id: pct}
              - retention_scores: {topic_id: pct}
              - concept_drift_score: float
            top_n: how many at-risk topics to return

        Returns: list of {topic_id, risk_score, reason}
        """
        mastery    = twin_state.get("verified_mastery", {})
        retention  = twin_state.get("retention_scores", {})
        drift      = twin_state.get("concept_drift_score", 0.0)

        if not mastery:
            return []

        if self.is_trained:
            return self._ml_predict(mastery, retention, drift, top_n)
        else:
            return self._rule_based_predict(mastery, retention, drift, top_n)

    def _rule_based_predict(self, mastery, retention, drift, top_n) -> list:
        """
        Rule-based risk scoring (no training data needed):
          risk = (1 - mastery/100) * 0.6 + (1 - retention/100) * 0.3 + drift_factor * 0.1
        """
        scores = []
        for topic_id, m_pct in mastery.items():
            r_pct = retention.get(topic_id, m_pct)  # fallback to mastery if no retention
            drift_factor = min(1.0, drift / 100.0)

            risk = (
                (1 - m_pct / 100) * 0.6 +
                (1 - r_pct / 100) * 0.3 +
                drift_factor * 0.1
            )

            if m_pct < 70:
                reason = f"Below threshold ({m_pct:.0f}%)"
            elif r_pct < m_pct - 10:
                reason = f"Retention dropping ({r_pct:.0f}% vs {m_pct:.0f}% mastery)"
            elif drift_factor > 0.5:
                reason = "High concept drift detected"
            else:
                reason = f"Marginal mastery ({m_pct:.0f}%)"

            scores.append({
                "topic_id":   topic_id,
                "risk_score": round(risk, 4),
                "reason":     reason,
            })

        scores.sort(key=lambda x: x["risk_score"], reverse=True)
        return scores[:top_n]

    def _ml_predict(self, mastery, retention, drift, top_n) -> list:
        """ML-based prediction using trained Random Forest."""
        scores = []
        for topic_id, m_pct in mastery.items():
            r_pct = retention.get(topic_id, m_pct)
            features = np.array([[m_pct, r_pct, drift]]).astype(np.float32)
            features_scaled = self.scaler.transform(features)
            risk = self.model.predict_proba(features_scaled)[0][1]  # probability of failure
            scores.append({
                "topic_id":   topic_id,
                "risk_score": round(float(risk), 4),
                "reason":     "ML prediction from session history",
            })

        scores.sort(key=lambda x: x["risk_score"], reverse=True)
        return scores[:top_n]

    def train(self, training_records: list) -> dict:
        """
        Train the Random Forest on accumulated session history.
        training_records: list of {mastery, retention, drift, failed (bool)}
        Only runs when enough data exists (min 50 records recommended).
        """
        if not SKLEARN_AVAILABLE:
            return {"error": "scikit-learn not available"}
        if len(training_records) < 10:
            return {"error": f"Need at least 10 records, got {len(training_records)}"}

        X = np.array([[r["mastery"], r["retention"], r["drift"]] for r in training_records])
        y = np.array([1 if r["failed"] else 0 for r in training_records])

        self.scaler = StandardScaler()
        X_scaled    = self.scaler.fit_transform(X)

        self.model  = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
        self.model.fit(X_scaled, y)
        self.is_trained = True

        self._model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model,  str(self._model_path))
        joblib.dump(self.scaler, str(self._scaler_path))

        logger.info(f"[WeakTopicPredictor] Trained on {len(training_records)} records")
        return {"status": "trained", "records": len(training_records)}


# Module-level singleton
_predictor = None

def get_predictor() -> WeakTopicPredictor:
    global _predictor
    if _predictor is None:
        _predictor = WeakTopicPredictor()
    return _predictor


def predict_at_risk_topics(twin_state: dict, top_n: int = 5) -> list:
    """Public API — used by Planner Agent."""
    return get_predictor().predict_at_risk(twin_state, top_n)

weak_topic_predictor = get_predictor()
