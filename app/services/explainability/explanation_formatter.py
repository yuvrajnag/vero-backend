from typing import List, Dict, Any
from app.services.explainability.feature_mapper import get_feature_name
from app.schemas.explain_schema import ExplanationDetail

def format_shap_explanation(
    shap_values: List[float], 
    feature_names: List[str], 
    top_k: int = 3, 
    is_percentage: bool = True
) -> List[ExplanationDetail]:
    """
    Format SHAP values into human-readable explanations.
    """
    explanations = []
    
    # Pair feature names with their shap values
    feature_impacts = list(zip(feature_names, shap_values))
    # Sort by absolute impact to get the most important features
    feature_impacts.sort(key=lambda x: abs(x[1]), reverse=True)
    
    for feature, impact in feature_impacts[:top_k]:
        # Skip features with very low impact
        if abs(impact) < 0.001:
            continue
            
        friendly_name = get_feature_name(feature)
        
        if is_percentage:
            impact_str = f"{'+' if impact > 0 else ''}{impact * 100:.1f}%"
        else:
            impact_str = f"{'+' if impact > 0 else ''}{impact:.2f}"
            
        if impact > 0:
            reason = f"High {friendly_name} positively impacted the outcome" if not is_percentage else f"High {friendly_name} increased probability"
        else:
            reason = f"Low {friendly_name} negatively impacted the outcome" if not is_percentage else f"Low {friendly_name} reduced probability"
            
        explanations.append(ExplanationDetail(
            feature=feature,
            impact=impact_str,
            reason=reason
        ))
        
    return explanations
