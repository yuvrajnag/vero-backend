import os
import numpy as np
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import IsolationForest
import joblib

MODELS_DIR = Path(__file__).parent

def generate_synthetic_data(num_samples: int = 1000):
    """
    Generate synthetic data for training the models.
    """
    np.random.seed(42)
    
    # Common features for techniciansno
    exp_years = np.random.uniform(0, 20, num_samples)
    completion_rate = np.random.uniform(0.5, 1.0, num_samples)
    avg_rating = np.random.uniform(2.5, 5.0, num_samples)
    total_jobs = np.random.poisson(50, num_samples)
    response_time = np.random.uniform(5, 120, num_samples)
    fraud_risk_hist = np.random.uniform(0, 0.4, num_samples)
    is_verified = np.random.binomial(1, 0.8, num_samples)
    base_rate = np.random.uniform(20, 100, num_samples)
    num_skills = np.random.poisson(5, num_samples)
    
    # Common features for jobs
    budget = np.random.uniform(50, 500, num_samples)
    urgency_level = np.random.randint(0, 3, num_samples) # 0: normal, 1: urgent, 2: emergency
    
    # 1. Success Probability Data
    # Feature order: [exp_years, completion_rate, avg_rating, total_jobs, response_time, fraud_risk_hist, is_verified, budget, urgency_is_emergency]
    X_success = np.column_stack([
        exp_years, completion_rate, avg_rating, total_jobs, response_time, 
        fraud_risk_hist, is_verified, budget, (urgency_level == 2).astype(float)
    ])
    
    # Synthetic logic for success
    success_prob = 0.5 + (exp_years * 0.01) + (completion_rate * 0.2) + ((avg_rating - 3) * 0.1) - (fraud_risk_hist * 0.3)
    y_success = (np.random.rand(num_samples) < success_prob).astype(int)
    
    # 2. Fair Price Data
    # Feature order: [exp_years, avg_rating, base_rate, num_skills, budget, urgency_score, is_verified]
    X_price = np.column_stack([
        exp_years, avg_rating, base_rate, num_skills, budget, urgency_level.astype(float), is_verified
    ])
    
    # Synthetic logic for price
    y_price = base_rate + (exp_years * 5) + ((avg_rating - 3) * 10) + (urgency_level * 20) + np.random.normal(0, 10, num_samples)
    y_price = np.maximum(20, y_price)
    
    # 3. Negotiation Acceptance Data
    # Feature order: [ratio, avg_rating, total_jobs, completion_rate, is_online]
    offered_prices = np.random.uniform(30, 150, num_samples)
    min_rate = base_rate * 0.8
    ratios = np.where(min_rate > 0, offered_prices / min_rate, 1.0)
    is_online = np.random.binomial(1, 0.5, num_samples)
    
    X_neg = np.column_stack([
        ratios, avg_rating, total_jobs, completion_rate, is_online
    ])
    
    # Synthetic logic for negotiation acceptance
    neg_prob = 1 / (1 + np.exp(-10 * (ratios - 0.95))) # Sigmoid centered around 0.95 ratio
    y_neg = (np.random.rand(num_samples) < neg_prob).astype(int)
    
    # 4. Fraud Risk Data
    # Feature order: [trust_score, completion_rate, avg_rating, total_jobs, response_time, fraud_risk_hist, is_verified]
    trust_score = np.random.uniform(40, 100, num_samples)
    # Add anomalies
    anomaly_indices = np.random.choice(num_samples, int(num_samples * 0.05), replace=False)
    trust_score[anomaly_indices] = np.random.uniform(0, 30, len(anomaly_indices))
    fraud_risk_hist[anomaly_indices] = np.random.uniform(0.6, 1.0, len(anomaly_indices))
    completion_rate[anomaly_indices] = np.random.uniform(0, 0.3, len(anomaly_indices))
    
    X_fraud = np.column_stack([
        trust_score, completion_rate, avg_rating, total_jobs, response_time, fraud_risk_hist, is_verified
    ])
    
    return {
        "success": (X_success, y_success),
        "price": (X_price, y_price),
        "neg": (X_neg, y_neg),
        "fraud": X_fraud
    }

def train_and_save_models():
    os.makedirs(MODELS_DIR, exist_ok=True)
    
    print("Generating synthetic data...")
    data = generate_synthetic_data(2000)
    
    print("Training Success Predictor (RandomForest)...")
    clf_success = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    clf_success.fit(data["success"][0], data["success"][1])
    joblib.dump(clf_success, MODELS_DIR / "success_model.joblib")
    
    print("Training Price Predictor (GradientBoostingRegressor)...")
    reg_price = GradientBoostingRegressor(n_estimators=100, learning_rate=0.1, max_depth=4, random_state=42)
    reg_price.fit(data["price"][0], data["price"][1])
    joblib.dump(reg_price, MODELS_DIR / "price_model.joblib")
    
    print("Training Negotiation Predictor (LogisticRegression)...")
    clf_neg = LogisticRegression(random_state=42)
    clf_neg.fit(data["neg"][0], data["neg"][1])
    joblib.dump(clf_neg, MODELS_DIR / "negotiation_model.joblib")
    
    print("Training Fraud Detector (IsolationForest)...")
    clf_fraud = IsolationForest(contamination=0.05, random_state=42)
    clf_fraud.fit(data["fraud"])
    joblib.dump(clf_fraud, MODELS_DIR / "fraud_model.joblib")
    
    print(f"All models trained and saved to {MODELS_DIR}")

if __name__ == "__main__":
    train_and_save_models()
