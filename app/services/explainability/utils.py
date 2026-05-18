from sqlmodel import Session
from typing import Dict, Any, Optional
from app.models.ai import ExplainabilityLog
from app.utils.logger import logger

def log_explanation(session: Session, model_name: str, prediction_id: Optional[str], explanation_json: Dict[str, Any]):
    """Log explainability results to the database."""
    try:
        log = ExplainabilityLog(
            model_name=model_name,
            prediction_id=prediction_id,
            explanation_json=explanation_json
        )
        session.add(log)
        session.commit()
    except Exception as e:
        logger.error(f"Failed to log explanation for {model_name}: {e}")
        session.rollback()
