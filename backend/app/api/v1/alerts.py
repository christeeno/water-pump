import json
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ...database import get_db
from ...models.telemetry import AlertEvent
from ...schemas.alerts import AlertEventResponse, AlertAckResponse

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _alert_to_schema(alert: AlertEvent) -> AlertEventResponse:
    try:
        evidence = json.loads(alert.sensor_evidence_json) if alert.sensor_evidence_json else {}
    except Exception:
        evidence = {}

    return AlertEventResponse(
        id=alert.id,
        event_id=alert.event_id,
        timestamp=alert.timestamp,
        severity=alert.severity,
        fault_category=alert.fault_category,
        description=alert.description,
        sensor_evidence_json=alert.sensor_evidence_json,
        sensor_evidence=evidence,
        pump_state=alert.pump_state,
        recommended_action=alert.recommended_action,
        acknowledged=alert.acknowledged,
        acknowledged_at=alert.acknowledged_at,
        device_id=alert.device_id,
    )


@router.get("", response_model=List[AlertEventResponse])
def get_alerts(
    device_id: Optional[str] = Query(None, description="Filter by device ID"),
    severity: Optional[str] = Query(None, description="Filter by severity (INFO, WARNING, CRITICAL)"),
    acknowledged: Optional[bool] = Query(None, description="Filter by acknowledged status"),
    limit: int = Query(100, ge=1, le=1000, description="Max alerts to return"),
    db: Session = Depends(get_db),
):
    """Query alerts with filtering by device, severity, and status."""
    query = db.query(AlertEvent)
    if device_id:
        query = query.filter(AlertEvent.device_id == device_id)
    if severity:
        query = query.filter(AlertEvent.severity == severity.upper())
    if acknowledged is not None:
        query = query.filter(AlertEvent.acknowledged == acknowledged)

    alerts = query.order_by(desc(AlertEvent.timestamp)).limit(limit).all()
    return [_alert_to_schema(a) for a in alerts]


@router.post("/{event_id}/ack", response_model=AlertAckResponse)
def acknowledge_alert(event_id: str, db: Session = Depends(get_db)):
    """Acknowledge an active alert event."""
    alert = db.query(AlertEvent).filter(AlertEvent.event_id == event_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with event_id '{event_id}' not found",
        )

    now = datetime.now(timezone.utc)
    alert.acknowledged = True
    alert.acknowledged_at = now
    db.commit()

    return AlertAckResponse(
        success=True,
        event_id=alert.event_id,
        acknowledged=True,
        acknowledged_at=now,
    )
