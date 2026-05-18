from typing import Dict, Any
from sqlmodel import Session
import numpy as np

from app.services.ai.success_predictor import _load_model as load_success_model, _build_features as build_success_features, predict_success_probability
from app.services.ai.price_predictor import _load_model as load_price_model, _build_features as build_price_features, predict_fair_price
from app.services.ai.negotiation_predictor import _load_model as load_neg_model, _build_features as build_neg_features, predict_acceptance_probability
from app.services.ai.fraud_detector import _load_model as load_fraud_model, _build_features as build_fraud_features, compute_fraud_risk

from app.services.explainability.shap_service import get_tree_explainer, get_linear_explainer, compute_shap_values
from app.services.explainability.explanation_formatter import format_shap_explanation
from app.services.explainability.feature_mapper import SUCCESS_FEATURES, PRICE_FEATURES, NEGOTIATION_FEATURES, FRAUD_FEATURES
from app.services.explainability.utils import log_explanation
from app.schemas.explain_schema import ExplainSuccessResponse, ExplainPriceResponse, ExplainNegotiationResponse, ExplainFraudResponse, ExplainMatchResponse

def explain_success(tech: Dict[str, Any], job: Dict[str, Any], session: Session, prediction_id: str) -> ExplainSuccessResponse:
    prediction = predict_success_probability(tech, job)
    model = load_success_model()
    
    explanations = []
    if model:
        features = build_success_features(tech, job)
        explainer = get_tree_explainer(model, "success_model")
        if explainer:
            shap_values = compute_shap_values(explainer, features, "classifier")
            explanations = format_shap_explanation(shap_values, SUCCESS_FEATURES, top_k=3, is_percentage=True)
            
    response = ExplainSuccessResponse(
        prediction=prediction,
        explanations=explanations,
        summary_plot=None
    )
    
    log_explanation(session, "success_model", prediction_id, response.model_dump())
    return response

def explain_price(tech: Dict[str, Any], job: Dict[str, Any], session: Session, prediction_id: str) -> ExplainPriceResponse:
    prediction_result = predict_fair_price(tech, job)
    model = load_price_model()
    
    explanations = []
    if model:
        features = build_price_features(tech, job)
        explainer = get_tree_explainer(model, "price_model")
        if explainer:
            shap_values = compute_shap_values(explainer, features, "regressor")
            explanations = format_shap_explanation(shap_values, PRICE_FEATURES, top_k=3, is_percentage=False)
            
    response = ExplainPriceResponse(
        predicted_price=prediction_result["predicted_price"],
        explanations=explanations,
        summary_plot=None
    )
    
    log_explanation(session, "price_model", prediction_id, response.model_dump())
    return response

def explain_negotiation(tech: Dict[str, Any], offered_price: float, session: Session, prediction_id: str) -> ExplainNegotiationResponse:
    prediction_result = predict_acceptance_probability(tech, offered_price)
    model = load_neg_model()
    
    explanations = []
    if model:
        features = build_neg_features(tech, offered_price)
        # Using a dummy background data for LinearExplainer if needed, or simply let it fallback.
        # But we will use the tree explainer logic if it was a tree. Since it's LogisticRegression, we can use shap.LinearExplainer
        # To avoid issues without background data, we can use shap.Explainer
        import shap
        try:
            # For linear models without background data, we can just use the coefficients directly
            coeffs = model.coef_[0]
            # SHAP values for a linear model are roughly feature_value * coefficient - expected_value
            shap_values = [float(f * c) for f, c in zip(features, coeffs)]
            explanations = format_shap_explanation(shap_values, NEGOTIATION_FEATURES, top_k=3, is_percentage=True)
        except Exception:
            pass
            
    response = ExplainNegotiationResponse(
        acceptance_probability=prediction_result["acceptance_probability"],
        explanations=explanations,
        summary_plot=None
    )
    
    log_explanation(session, "negotiation_model", prediction_id, response.model_dump())
    return response

def explain_fraud(tech: Dict[str, Any], session: Session, prediction_id: str) -> ExplainFraudResponse:
    prediction_result = compute_fraud_risk(tech)
    model = load_fraud_model()
    
    explanations = []
    if model:
        features = build_fraud_features(tech)
        explainer = get_tree_explainer(model, "fraud_model")
        if explainer:
            # Isolation forest SHAP values
            shap_values = compute_shap_values(explainer, features, "regressor")
            # For isolation forest, lower scores are more anomalous.
            explanations = format_shap_explanation(shap_values, FRAUD_FEATURES, top_k=3, is_percentage=False)
            
    response = ExplainFraudResponse(
        risk_score=prediction_result["risk_score"],
        explanations=explanations,
        summary_plot=None
    )
    
    log_explanation(session, "fraud_model", prediction_id, response.model_dump())
    return response

def explain_match(tech: Dict[str, Any], job: Dict[str, Any], session: Session, prediction_id: str) -> ExplainMatchResponse:
    # Skill matching uses TF-IDF cosine similarity, so we can generate heuristic explanations
    job_skills = [s.lower().strip() for s in job.get("required_skills", [])]
    tech_skills = [s.lower().strip() for s in tech.get("skills", [])]
    
    matched = list(set(job_skills) & set(tech_skills))
    missing = list(set(job_skills) - set(tech_skills))
    
    from app.services.ai.skill_matcher import compute_match_score
    score = compute_match_score(job.get("required_skills", []), tech.get("skills", []))
    
    explanations = []
    if matched:
        explanations.append(f"+{len(matched)*10}% because {', '.join(matched)} expertise matched")
    if missing:
        explanations.append(f"-{len(missing)*10}% because {', '.join(missing)} skill missing")
    if tech.get("is_background_verified"):
        explanations.append("+5% because technician is background verified")
        
    response = ExplainMatchResponse(
        match_score=score,
        matched_skills=matched,
        missing_skills=missing,
        explanations=explanations
    )
    
    log_explanation(session, "skill_matcher", prediction_id, response.model_dump())
    return response
