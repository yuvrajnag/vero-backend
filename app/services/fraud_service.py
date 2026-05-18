from sqlmodel import Session, select
from fastapi import HTTPException
from app.models.fraud import FraudDetectionLog
from app.models.technician import Technician
from typing import List, Optional
import uuid
from datetime import datetime, timezone

def log_fraud_event(
    session: Session,
    technician_id: uuid.UUID,
    risk_score: float,
    fraud_reason: str,
) -> FraudDetectionLog:
    log = FraudDetectionLog(
        technician_id=technician_id,
        risk_score=risk_score,
        fraud_reason=fraud_reason,
    )
    session.add(log)

    # Update technician risk score
    tech = session.get(Technician, technician_id)
    if tech:
        # Weighted rolling average: 70% old + 30% new
        tech.fraud_risk_score = round(tech.fraud_risk_score * 0.7 + risk_score * 0.3, 4)
        session.add(tech)

    session.commit()
    session.refresh(log)
    return log

def resolve_fraud_event(
    session: Session,
    event_id: uuid.UUID,
    admin_id: uuid.UUID,
    action_taken: str,
) -> FraudDetectionLog:
    log = session.get(FraudDetectionLog, event_id)
    if not log:
        raise HTTPException(status_code=404, detail="Fraud log not found")
    log.action_taken = action_taken
    log.reviewed_by = admin_id
    log.resolved_at = datetime.now(timezone.utc)
    session.add(log)
    session.commit()
    session.refresh(log)
    return log

def get_fraud_logs(session: Session, resolved: Optional[bool] = None, limit: int = 100) -> List[FraudDetectionLog]:
    query = select(FraudDetectionLog)
    if resolved is True:
        query = query.where(FraudDetectionLog.resolved_at != None)
    elif resolved is False:
        query = query.where(FraudDetectionLog.resolved_at == None)
    return list(session.exec(query.order_by(FraudDetectionLog.created_at.desc()).limit(limit)).all())

def get_technician_fraud_logs(session: Session, technician_id: uuid.UUID) -> List[FraudDetectionLog]:
    return list(session.exec(
        select(FraudDetectionLog)
        .where(FraudDetectionLog.technician_id == technician_id)
        .order_by(FraudDetectionLog.created_at.desc())
    ).all())
