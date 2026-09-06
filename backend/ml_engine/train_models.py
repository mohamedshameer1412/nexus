"""
ML Model Training Script
Trains and saves ML models for the adaptive learning system.
Run this script to generate trained models.
"""
import os
import sys
import django
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from quiz.models import Response, QuizSession
from django.contrib.auth import get_user_model

User = get_user_model()


def generate_synthetic_training_data(n_samples=1000):
    """
    Generate synthetic training data for weak topic prediction.
    In production, this would use real historical data.
    """
    print(f"Generating {n_samples} synthetic training samples...")
    
    training_data = []
    
    for i in range(n_samples):
        # Generate random features
        accuracy = np.random.uniform(0.3, 0.95)
        avg_response_time = np.random.uniform(5, 40)
        hesitation_rate = np.random.uniform(0, 0.3)
        tab_switch_rate = np.random.uniform(0, 0.15)
        performance_trend = np.random.uniform(-0.2, 0.2)
        
        # Determine if topic is weak based on features
        # Lower accuracy, higher response time, more hesitation = weak topic
        weakness_score = (
            (1 - accuracy) * 0.5 +
            (avg_response_time / 40) * 0.2 +
            hesitation_rate * 0.2 +
            tab_switch_rate * 0.1
        )
        
        is_weak = weakness_score > 0.5
        
        features = np.array([
            accuracy,
            avg_response_time,
            hesitation_rate,
            tab_switch_rate,
            performance_trend
        ])
        
        training_data.append({
            'features': features,
            'is_weak': is_weak
        })
    
    return training_data


def train_weak_topic_predictor():
    """Train Random Forest model for weak topic prediction"""
    print("\n" + "="*60)
    print("TRAINING WEAK TOPIC PREDICTOR")
    print("="*60)
    
    # Generate training data
    training_data = generate_synthetic_training_data(1000)
    
    # Prepare data
    X = np.array([d['features'] for d in training_data])
    y = np.array([d['is_weak'] for d in training_data])
    
    print(f"Training samples: {len(X)}")
    print(f"Weak topics: {sum(y)} ({sum(y)/len(y)*100:.1f}%)")
    
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Train model
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        n_jobs=-1
    )
    
    print("Training Random Forest...")
    model.fit(X_scaled, y)
    
    # Evaluate
    train_accuracy = model.score(X_scaled, y)
    print(f"Training accuracy: {train_accuracy*100:.2f}%")
    
    # Feature importance
    feature_names = ['Accuracy', 'Response Time', 'Hesitation', 'Tab Switches', 'Trend']
    importances = model.feature_importances_
    
    print("\nFeature Importances:")
    for name, importance in zip(feature_names, importances):
        print(f"  {name}: {importance:.3f}")
    
    # Save model
    model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ml_models')
    os.makedirs(model_dir, exist_ok=True)
    
    model_path = os.path.join(model_dir, 'weak_topic_predictor.pkl')
    
    model_data = {
        'model': model,
        'scaler': scaler,
        'is_trained': True,
        'feature_names': feature_names,
        'train_accuracy': train_accuracy
    }
    
    joblib.dump(model_data, model_path)
    print(f"\n✓ Model saved to: {model_path}")
    
    return model, scaler


def train_irt_calibration():
    """
    Calibrate IRT parameters for existing questions.
    This would normally use historical response data.
    """
    print("\n" + "="*60)
    print("CALIBRATING IRT PARAMETERS")
    print("="*60)
    
    from quiz.models import Question
    
    questions = Question.objects.all()
    
    if not questions.exists():
        print("No questions found in database. Skipping IRT calibration.")
        return
    
    print(f"Calibrating {questions.count()} questions...")
    
    for question in questions:
        # Set IRT parameters based on difficulty level
        # In production, these would be estimated from response data
        difficulty_map = {
            1: -1.5,  # Very Easy
            2: -0.5,  # Easy
            3: 0.0,   # Medium
            4: 0.5,   # Hard
            5: 1.5,   # Very Hard
        }
        
        question.irt_difficulty = difficulty_map.get(question.difficulty_level, 0.0)
        question.irt_discrimination = 1.0 + np.random.uniform(-0.2, 0.2)  # Add slight variation
        question.save()
    
    print("✓ IRT parameters calibrated for all questions")


def train_performance_predictor():
    """Train XGBoost model for performance prediction"""
    print("\n" + "="*60)
    print("TRAINING PERFORMANCE PREDICTOR")
    print("="*60)
    
    from ml_engine.performance_predictor import performance_predictor
    
    # Generate synthetic training data
    # Features: [avg_score_last_5, trend, avg_response_time, consistency, quiz_freq, topic_div, diff_prog, beh_score, hes_rate, tab_sw]
    print("Generating synthetic training data for Performance Predictor...")
    training_data = []
    
    for _ in range(1000):
        # Good student
        if np.random.random() > 0.5:
             avg_score = np.random.uniform(70, 100)
             trend = np.random.uniform(0, 10)
             resp_time = np.random.uniform(5, 20)
             consistency = np.random.uniform(5, 15)
             beh_score = np.random.uniform(80, 100)
             target = min(100, avg_score + np.random.uniform(-5, 10))
        # Struggling student
        else:
             avg_score = np.random.uniform(30, 70)
             trend = np.random.uniform(-10, 5)
             resp_time = np.random.uniform(20, 60)
             consistency = np.random.uniform(10, 30)
             beh_score = np.random.uniform(40, 80)
             target = max(0, avg_score + np.random.uniform(-10, 5))
             
        features = np.array([
            avg_score,
            trend,
            resp_time,
            consistency,
            np.random.uniform(0, 5), # freq
            np.random.uniform(1, 10), # div
            np.random.uniform(1, 5), # diff
            beh_score,
            np.random.uniform(0, 5), # hes
            np.random.uniform(0, 5) # tab
        ])
        
        training_data.append((features, target))
        
    print(f"Training XGBoost on {len(training_data)} samples...")
    success = performance_predictor.train(training_data)
    
    if success:
        model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ml_models')
        os.makedirs(model_dir, exist_ok=True)
        model_path = os.path.join(model_dir, 'performance_predictor.pkl')
        performance_predictor.save_model(model_path)
        print(f"✓ Performance model saved to: {model_path}")
    else:
        print("x Failed to train performance model")


def main():
    """Main training function"""
    print("="*60)
    print("ML MODEL TRAINING SCRIPT")
    print("="*60)
    print("\nThis script trains and saves ML models for:")
    print("  1. Weak Topic Predictor (Random Forest)")
    print("  2. IRT Parameter Calibration")
    print("\n" + "="*60)
    
    # Train weak topic predictor
    model, scaler = train_weak_topic_predictor()
    
    # Train performance predictor
    train_performance_predictor()
    
    # Calibrate IRT parameters
    
    # Calibrate IRT parameters
    train_irt_calibration()
    
    # Train engagement detector
    train_engagement_detector()
    
    print("\n" + "="*60)
    print("TRAINING COMPLETE!")
    print("="*60)
    print("\nTrained models:")
    print("  ✓ Weak Topic Predictor (Random Forest)")
    print("  ✓ Performance Predictor (XGBoost)")
    print("  ✓ Engagement Detector (Neural Network)")
    print("  ✓ IRT Parameters Calibrated")
    print("\nModels are ready for use in the API!")


def train_engagement_detector():
    """Train Neural Network for engagement detection"""
    print("\n" + "="*60)
    print("TRAINING ENGAGEMENT DETECTOR")
    print("="*60)
    
    from ml_engine.engagement_detector import engagement_detector
    
    # Generate synthetic training data
    # Features: [resp_mean, resp_std, resp_trend, acc_1, acc_2, hes_rate, tab_switch, conf_mean, conf_trend, resp_acc]
    print("Generating synthetic training data for Engagement Detector...")
    training_data = []
    
    for _ in range(1000):
        # Engaged student
        if np.random.random() < 0.33:
             features = np.array([
                 np.random.uniform(5, 15), # resp_mean
                 np.random.uniform(1, 5),  # resp_std
                 np.random.uniform(-2, 2), # resp_trend (steady)
                 np.random.uniform(0.8, 1.0), # acc_1
                 np.random.uniform(0.8, 1.0), # acc_2
                 np.random.uniform(0, 1), # hes
                 0, # tab
                 np.random.uniform(4, 5), # conf
                 np.random.uniform(0, 1), # conf_trend
                 np.random.uniform(-1, 1) # acc
             ])
             label = 0 # engaged
        # Fatigued student
        elif np.random.random() < 0.66:
             features = np.array([
                 np.random.uniform(15, 40), # resp_mean (slower)
                 np.random.uniform(5, 15), # resp_std (variable)
                 np.random.uniform(5, 15), # resp_trend (slowing down)
                 np.random.uniform(0.7, 0.9), # acc_1
                 np.random.uniform(0.4, 0.7), # acc_2 (dropping)
                 np.random.uniform(2, 5), # hes
                 np.random.uniform(0, 2), # tab
                 np.random.uniform(2, 4), # conf
                 np.random.uniform(-2, 0), # conf_trend (dropping)
                 np.random.uniform(2, 10) # acc (slowing)
             ])
             label = 2 # fatigued
        # Neutral
        else:
             features = np.array([
                 np.random.uniform(10, 25), 
                 np.random.uniform(3, 8),
                 np.random.uniform(-1, 3),
                 np.random.uniform(0.6, 0.85),
                 np.random.uniform(0.6, 0.85),
                 np.random.uniform(1, 3),
                 np.random.uniform(0, 1), 
                 np.random.uniform(3, 4), 
                 np.random.uniform(-1, 1), 
                 np.random.uniform(-1, 2)
             ])
             label = 1 # neutral
             
        training_data.append((features, label))
        
    print(f"Training Neural Network on {len(training_data)} samples...")
    success = engagement_detector.train(training_data, epochs=20)
    
    if success:
        model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ml_models')
        os.makedirs(model_dir, exist_ok=True)
        model_path = os.path.join(model_dir, 'engagement_detector.keras')
        scaler_path = os.path.join(model_dir, 'engagement_scaler.pkl')
        engagement_detector.save_model(model_path, scaler_path)
        print(f"✓ Engagement model saved to: {model_path}")
    else:
        print("x Failed to train engagement model") 



if __name__ == '__main__':
    main()
