"""
Neural Network Engagement Detector
Detects student engagement and fatigue using deep learning
"""
import numpy as np
try:
    from tensorflow import keras
    from tensorflow.keras import layers
except ImportError:
    keras = None
    layers = None
from sklearn.preprocessing import StandardScaler
import joblib
import logging

logger = logging.getLogger(__name__)


class EngagementDetector:
    """Detect engagement level using Neural Network"""
    
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        self.engagement_labels = ['engaged', 'neutral', 'fatigued']
    
    def extract_features(self, session_responses):
        """
        Extract time-series features from quiz session
        Features:
        - Response time variance
        - Accuracy trend (first half vs second half)
        - Hesitation pattern
        - Tab switch frequency
        - Confidence level trend
        - Response time acceleration
        """
        if not session_responses:
            return None
        
        responses = list(session_responses)
        n = len(responses)
        
        if n < 3:
            return None
        
        # Split into halves
        first_half = responses[:n//2]
        second_half = responses[n//2:]
        
        features = {
            'response_time_mean': np.mean([r.response_time for r in responses]),
            'response_time_std': np.std([r.response_time for r in responses]),
            'response_time_trend': np.mean([r.response_time for r in second_half]) - np.mean([r.response_time for r in first_half]),
            'accuracy_first_half': sum(1 for r in first_half if r.is_correct) / len(first_half),
            'accuracy_second_half': sum(1 for r in second_half if r.is_correct) / len(second_half),
            'hesitation_rate': np.mean([r.hesitation_count for r in responses]),
            'tab_switch_rate': np.mean([r.tab_switches for r in responses]),
            'confidence_mean': np.mean([r.confidence_level for r in responses]),
            'confidence_trend': np.mean([r.confidence_level for r in second_half]) - np.mean([r.confidence_level for r in first_half]),
            'response_acceleration': (responses[-1].response_time - responses[0].response_time) / n
        }
        
        return np.array(list(features.values()))
    
    def build_model(self, input_dim=10):
        """Build neural network architecture"""
        model = keras.Sequential([
            layers.Dense(64, activation='relu', input_dim=input_dim),
            layers.Dropout(0.3),
            layers.Dense(32, activation='relu'),
            layers.Dropout(0.2),
            layers.Dense(16, activation='relu'),
            layers.Dense(3, activation='softmax')  # 3 classes: engaged, neutral, fatigued
        ])
        
        model.compile(
            optimizer='adam',
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )
        
        return model
    
    def train(self, training_data, epochs=50):
        """
        Train neural network
        training_data: list of (features, label) tuples
        label: 0=engaged, 1=neutral, 2=fatigued
        """
        if len(training_data) < 20:
            logger.warning("Insufficient training data for Neural Network")
            return False
        
        X = np.array([d[0] for d in training_data])
        y = np.array([d[1] for d in training_data])
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Build and train model
        self.model = self.build_model(input_dim=X.shape[1])
        
        history = self.model.fit(
            X_scaled, y,
            epochs=epochs,
            batch_size=8,
            validation_split=0.2,
            verbose=0
        )
        
        self.is_trained = True
        
        final_accuracy = history.history['accuracy'][-1]
        logger.info(f"Neural Network trained with accuracy: {final_accuracy:.2f}")
        
        return True
    
    def predict(self, features):
        """Predict engagement level"""
        if not self.is_trained:
            logger.warning("Model not trained, returning default prediction")
            return 'neutral'
        
        features_scaled = self.scaler.transform([features])
        prediction = self.model.predict(features_scaled, verbose=0)[0]
        
        # Get class with highest probability
        class_idx = np.argmax(prediction)
        confidence = prediction[class_idx]
        
        return {
            'engagement_level': self.engagement_labels[class_idx],
            'confidence': float(confidence),
            'probabilities': {
                'engaged': float(prediction[0]),
                'neutral': float(prediction[1]),
                'fatigued': float(prediction[2])
            }
        }
    
    def save_model(self, model_path, scaler_path):
        """Save trained model"""
        if not self.is_trained:
            logger.warning("Cannot save untrained model")
            return False
        
        self.model.save(model_path)
        joblib.dump(self.scaler, scaler_path)
        
        logger.info(f"Neural Network model saved")
        return True
    
    def load_model(self, model_path, scaler_path):
        """Load trained model"""
        try:
            self.model = keras.models.load_model(model_path)
            self.scaler = joblib.load(scaler_path)
            self.is_trained = True
            
            logger.info(f"Neural Network model loaded")
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            return False


# Global instance
engagement_detector = EngagementDetector()
