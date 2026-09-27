"""
XGBoost Performance Predictor
Predicts future quiz performance based on historical data
"""
import xgboost as xgb
import numpy as np
from sklearn.preprocessing import StandardScaler
import joblib
import logging

logger = logging.getLogger(__name__)


class PerformancePredictor:
    """Predict student performance using XGBoost"""
    
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
    
    def extract_features(self, user_responses):
        """
        Extract features from user's quiz history
        Features:
        - Average score (last 5 quizzes)
        - Score trend (improving/declining)
        - Average response time
        - Consistency (std dev of scores)
        - Study frequency (quizzes per week)
        - Topic diversity
        - Difficulty progression
        """
        from quiz.models import QuizSession
        
        sessions = QuizSession.objects.filter(
            user=user_responses.first().session.user,
            is_active=False
        ).order_by('-completed_at')[:10]
        
        if not sessions.exists():
            return None
        
        scores = [s.total_score for s in sessions]
        
        features = {
            'avg_score_last_5': np.mean(scores[:5]) if len(scores) >= 5 else np.mean(scores),
            'score_trend': (scores[0] - scores[-1]) / len(scores) if len(scores) > 1 else 0,
            'avg_response_time': np.mean([s.avg_response_time for s in sessions]),
            'score_consistency': np.std(scores),
            'quiz_frequency': len(sessions) / 7,  # Quizzes per week
            'topic_diversity': len(set(s.quiz.topics.first().id for s in sessions if s.quiz.topics.exists())),
            'difficulty_progression': np.mean([s.current_difficulty_level for s in sessions]),
            'behavior_score_avg': np.mean([s.behavior_score for s in sessions]),
            'hesitation_rate': np.mean([s.total_hesitations for s in sessions]),
            'tab_switch_rate': np.mean([s.total_tab_switches for s in sessions])
        }
        
        return np.array(list(features.values()))
    
    def train(self, training_data):
        """
        Train XGBoost model
        training_data: list of (features, target_score) tuples
        """
        if len(training_data) < 10:
            logger.warning("Insufficient training data for XGBoost")
            return False
        
        X = np.array([d[0] for d in training_data])
        y = np.array([d[1] for d in training_data])
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train XGBoost
        self.model = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42
        )
        
        self.model.fit(X_scaled, y)
        self.is_trained = True
        
        logger.info("XGBoost model trained successfully")
        return True
    
    def predict(self, features):
        """Predict next quiz score"""
        if not self.is_trained:
            logger.warning("Model not trained, returning default prediction")
            return 50.0
        
        features_scaled = self.scaler.transform([features])
        prediction = self.model.predict(features_scaled)[0]
        
        # Clip to valid score range
        return np.clip(prediction, 0, 100)
    
    def save_model(self, path):
        """Save trained model"""
        if not self.is_trained:
            logger.warning("Cannot save untrained model")
            return False
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'is_trained': self.is_trained
        }
        
        joblib.dump(model_data, path)
        logger.info(f"XGBoost model saved to {path}")
        return True
    
    def load_model(self, path):
        """Load trained model"""
        try:
            model_data = joblib.load(path)
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.is_trained = model_data['is_trained']
            
            logger.info(f"XGBoost model loaded from {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            return False


# Global instance
performance_predictor = PerformancePredictor()
