import json
from datetime import datetime, timezone
from typing import Optional, List, Dict
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ...database import get_db
from ...models.telemetry import TelemetryRecord, AlertEvent, DeviceInfo, SystemSettings
from ...schemas.telemetry import (
    TelemetryCreate,
    TelemetryIngestResponse,
    TelemetryResponse,
    SensorValidationSummary,
)
from ...services.sensor_validation import UltrasonicValidator, calculate_tank_level
from ...services.fault_detection import evaluate_all_faults
from ...services.websocket_manager import manager
from ..deps import verify_device_api_key

router = APIRouter(prefix="/telemetry", tags=["telemetry"])

# Per-device sensor validators cache
_validators: Dict[str, UltrasonicValidator] = {}


def get_validator(device_id: str) -> UltrasonicValidator:
    if device_id not in _validators:
        _validators[device_id] = UltrasonicValidator()
    return _validators[device_id]


@router.post("", response_model=TelemetryIngestResponse, status_code=status.HTTP_200_OK)
async def ingest_telemetry(
    payload: TelemetryCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_device_api_key),
):
    """Ingest sensor telemetry from water controller device."""
    device_id = payload.device_id
    now = datetime.now(timezone.utc)

    # 1. Fetch or create device settings
    sys_settings = db.query(SystemSettings).filter(SystemSettings.device_id == device_id).first()
    if not sys_settings:
        sys_settings = SystemSettings(
            device_id=device_id,
            tank_height_cm=100.0,
            empty_distance_cm=95.0,
            full_distance_cm=15.0,
            low_level_threshold=20.0,
            high_level_threshold=90.0,
            min_flow_lpm=0.5,
            max_flow_lpm=30.0,
            min_pressure_bar=0.5,
            max_pressure_bar=3.5,
            max_current_a=5.0,
        )
        db.add(sys_settings)
        db.flush()

    # 2. Sensor validation
    validator = get_validator(device_id)
    validation_res = validator.validate(payload.tank_distance_cm, payload.timestamp)

    tank_level_valid = validation_res.is_valid
    filtered_distance = validation_res.filtered_value if validation_res.filtered_value is not None else payload.tank_distance_cm

    # Compute or validate tank level percentage
    if validation_res.is_valid and filtered_distance is not None:
        try:
            computed_level = calculate_tank_level(
                filtered_distance=filtered_distance,
                empty_distance=sys_settings.empty_distance_cm,
                full_distance=sys_settings.full_distance_cm,
            )
        except Exception:
            computed_level = payload.tank_level_percent if payload.tank_level_percent is not None else 0.0
    else:
        computed_level = payload.tank_level_percent if payload.tank_level_percent is not None else 0.0

    final_level = payload.tank_level_percent if payload.tank_level_percent is not None else computed_level

    # 3. Fetch recent telemetry records for fault detection (e.g. leakage check)
    recent_records = (
        db.query(TelemetryRecord)
        .filter(TelemetryRecord.device_id == device_id)
        .order_by(desc(TelemetryRecord.timestamp))
        .limit(5)
        .all()
    )

    sensor_status_dict = payload.sensor_status
    if hasattr(sensor_status_dict, "model_dump"):
        sensor_status_dict = sensor_status_dict.model_dump()
    elif not isinstance(sensor_status_dict, dict):
        sensor_status_dict = {"status": str(sensor_status_dict)}

    # 4. Fault Detection
    telemetry_dict_for_faults = {
        "device_id": device_id,
        "timestamp": payload.timestamp,
        "flow_rate_lpm": payload.flow_rate_lpm,
        "pressure_bar": payload.pressure_bar,
        "pump_current_a": payload.pump_current_a,
        "pump_on": payload.pump_on,
        "mode": payload.mode,
        "controller_state": payload.controller_state,
        "tank_level_percent": final_level,
        "sensor_status": sensor_status_dict,
    }

    detected_alerts = evaluate_all_faults(
        telemetry=telemetry_dict_for_faults,
        settings=sys_settings,
        recent_telemetry=recent_records,
    )

    # 5. Save alerts to DB
    alerts_created_count = 0
    for alert_data in detected_alerts:
        alert_obj = AlertEvent(
            event_id=alert_data["event_id"],
            timestamp=alert_data["timestamp"],
            severity=alert_data["severity"],
            fault_category=alert_data["fault_category"],
            description=alert_data["description"],
            sensor_evidence_json=alert_data["sensor_evidence_json"],
            pump_state=alert_data["pump_state"],
            recommended_action=alert_data["recommended_action"],
            acknowledged=False,
            device_id=device_id,
        )
        db.add(alert_obj)
        alerts_created_count += 1

    # 6. Save TelemetryRecord
    record = TelemetryRecord(
        device_id=device_id,
        timestamp=payload.timestamp,
        tank_distance_cm=filtered_distance if filtered_distance is not None else payload.tank_distance_cm,
        tank_level_percent=final_level,
        flow_rate_lpm=payload.flow_rate_lpm,
        pressure_bar=payload.pressure_bar,
        pump_current_a=payload.pump_current_a,
        pump_on=payload.pump_on,
        mode=payload.mode,
        controller_state=payload.controller_state,
        sensor_status_json=json.dumps(sensor_status_dict),
        is_simulated=False,
        raw_tank_distance_cm=payload.tank_distance_cm,
        tank_level_valid=tank_level_valid,
    )
    db.add(record)

    # 7. Update DeviceInfo
    device = db.query(DeviceInfo).filter(DeviceInfo.device_id == device_id).first()
    if not device:
        device = DeviceInfo(
            device_id=device_id,
            firmware_version="1.0.0",
            last_seen=now,
            last_telemetry_at=payload.timestamp,
            is_connected=True,
            controller_state=payload.controller_state,
            sensor_health_json=json.dumps(sensor_status_dict),
        )
        db.add(device)
    else:
        device.last_seen = now
        device.last_telemetry_at = payload.timestamp
        device.is_connected = True
        device.controller_state = payload.controller_state
        device.sensor_health_json = json.dumps(sensor_status_dict)

    db.commit()
    db.refresh(record)

    # 8. Broadcast to WebSocket clients
    broadcast_data = {
        "type": "telemetry_update",
        "device_id": device_id,
        "telemetry": {
            "id": record.id,
            "device_id": record.device_id,
            "timestamp": record.timestamp.isoformat(),
            "tank_distance_cm": record.tank_distance_cm,
            "tank_level_percent": record.tank_level_percent,
            "flow_rate_lpm": record.flow_rate_lpm,
            "pressure_bar": record.pressure_bar,
            "pump_current_a": record.pump_current_a,
            "pump_on": record.pump_on,
            "mode": record.mode,
            "controller_state": record.controller_state,
            "sensor_status": sensor_status_dict,
            "is_simulated": record.is_simulated,
        },
        "alerts_count": alerts_created_count,
        "new_alerts": detected_alerts,
    }
    await manager.broadcast(broadcast_data)

    validation_summary = SensorValidationSummary(
        raw_value=validation_res.raw_value,
        filtered_value=validation_res.filtered_value,
        is_valid=validation_res.is_valid,
        status=validation_res.status,
        last_valid=validation_res.last_valid,
        is_stale=validation_res.is_stale,
        tank_level_percent=final_level,
    )

    return TelemetryIngestResponse(
        status="success",
        device_id=device_id,
        telemetry_id=record.id,
        validation=validation_summary,
        alerts_generated=alerts_created_count,
    )


def _record_to_schema(r: TelemetryRecord) -> TelemetryResponse:
    try:
        status_dict = json.loads(r.sensor_status_json)
    except Exception:
        status_dict = {}
    return TelemetryResponse(
        id=r.id,
        device_id=r.device_id,
        timestamp=r.timestamp,
        tank_distance_cm=r.tank_distance_cm,
        tank_level_percent=r.tank_level_percent,
        flow_rate_lpm=r.flow_rate_lpm,
        pressure_bar=r.pressure_bar,
        pump_current_a=r.pump_current_a,
        pump_on=r.pump_on,
        mode=r.mode,
        controller_state=r.controller_state,
        sensor_status_json=r.sensor_status_json,
        sensor_status=status_dict,
        is_simulated=r.is_simulated,
        raw_tank_distance_cm=r.raw_tank_distance_cm,
        tank_level_valid=r.tank_level_valid,
    )


@router.get("/latest", response_model=TelemetryResponse)
def get_latest_telemetry(
    device_id: Optional[str] = Query(None, description="Filter by device ID"),
    db: Session = Depends(get_db),
):
    """Retrieve the most recent telemetry record."""
    query = db.query(TelemetryRecord)
    if device_id:
        query = query.filter(TelemetryRecord.device_id == device_id)
    latest = query.order_by(desc(TelemetryRecord.timestamp)).first()

    if not latest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No telemetry records found",
        )

    return _record_to_schema(latest)


@router.get("/history", response_model=List[TelemetryResponse])
def get_telemetry_history(
    device_id: Optional[str] = Query(None, description="Filter by device ID"),
    limit: int = Query(100, ge=1, le=1000, description="Max number of records"),
    start_time: Optional[datetime] = Query(None, description="Start timestamp"),
    end_time: Optional[datetime] = Query(None, description="End timestamp"),
    db: Session = Depends(get_db),
):
    """Retrieve historical telemetry records."""
    query = db.query(TelemetryRecord)
    if device_id:
        query = query.filter(TelemetryRecord.device_id == device_id)
    if start_time:
        query = query.filter(TelemetryRecord.timestamp >= start_time)
    if end_time:
        query = query.filter(TelemetryRecord.timestamp <= end_time)

    records = query.order_by(desc(TelemetryRecord.timestamp)).limit(limit).all()
    return [_record_to_schema(r) for r in records]
