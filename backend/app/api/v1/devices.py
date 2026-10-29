import json
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...database import get_db
from ...models.telemetry import DeviceInfo
from ...schemas.devices import DeviceInfoResponse

router = APIRouter(prefix="/devices", tags=["devices"])

STALE_THRESHOLD_SECONDS = 60.0


def _build_device_response(device: DeviceInfo) -> DeviceInfoResponse:
    now = datetime.now(timezone.utc)
    last_seen = device.last_seen
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)

    # Compute live is_connected status: stale if last_seen > 60s ago
    diff_seconds = (now - last_seen).total_seconds()
    is_live_connected = diff_seconds <= STALE_THRESHOLD_SECONDS

    try:
        health_dict = json.loads(device.sensor_health_json) if device.sensor_health_json else {}
    except Exception:
        health_dict = {}

    return DeviceInfoResponse(
        id=device.id,
        device_id=device.device_id,
        firmware_version=device.firmware_version,
        last_seen=device.last_seen,
        last_telemetry_at=device.last_telemetry_at,
        is_connected=is_live_connected,
        controller_state=device.controller_state,
        sensor_health_json=device.sensor_health_json,
        sensor_health=health_dict,
    )


@router.get("", response_model=List[DeviceInfoResponse])
def list_devices(db: Session = Depends(get_db)):
    """List all registered devices with live connectivity status."""
    devices = db.query(DeviceInfo).all()
    return [_build_device_response(d) for d in devices]


@router.get("/{device_id}", response_model=DeviceInfoResponse)
def get_device(device_id: str, db: Session = Depends(get_db)):
    """Retrieve details for a specific device."""
    device = db.query(DeviceInfo).filter(DeviceInfo.device_id == device_id).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device '{device_id}' not found",
        )
    return _build_device_response(device)
