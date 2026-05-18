import shap
import numpy as np
from typing import Dict, Any, List, Optional
from app.utils.logger import logger

# Cache explainers to avoid recomputing
_explainers_cache = {}

def get_tree_explainer(model: Any, model_name: str) -> Any:
    """Get or create a SHAP TreeExplainer for tree-based models."""
    if model_name in _explainers_cache:
        return _explainers_cache[model_name]
    
    try:
        explainer = shap.TreeExplainer(model)
        _explainers_cache[model_name] = explainer
        return explainer
    except Exception as e:
        logger.error(f"Failed to create TreeExplainer for {model_name}: {e}")
        return None

def get_linear_explainer(model: Any, model_name: str, background_data: Any) -> Any:
    """Get or create a SHAP LinearExplainer for linear models."""
    if model_name in _explainers_cache:
        return _explainers_cache[model_name]
    
    try:
        explainer = shap.LinearExplainer(model, background_data)
        _explainers_cache[model_name] = explainer
        return explainer
    except Exception as e:
        logger.error(f"Failed to create LinearExplainer for {model_name}: {e}")
        return None

def compute_shap_values(explainer: Any, features: List[float], model_type: str = "classifier") -> List[float]:
    """Compute SHAP values for a single instance."""
    try:
        features_array = np.array(features).reshape(1, -1)
        shap_values = explainer.shap_values(features_array)
        
        # Handle different shapes depending on model type
        if isinstance(shap_values, list):
            # RandomForest classification returns a list, one array per class
            return shap_values[1][0].tolist()
        elif shap_values.ndim == 3:
            return shap_values[0, :, 1].tolist()
        elif shap_values.ndim == 2:
            return shap_values[0].tolist()
        else:
            return shap_values.tolist()
    except Exception as e:
        logger.error(f"Failed to compute SHAP values: {e}")
        return [0.0] * len(features)
