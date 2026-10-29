from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...database import get_db
from ...models.telemetry import SystemSettings
from ...schemas.settings import SystemSettingsResponse, SystemSettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


def _get_or_create_default_settings(db: Session, device_id: str) -> SystemSettings:
    settings_obj = db.query(SystemSettings).filter(SystemSettings.device_id == device_id).first()
    if not settings_obj:
        settings_obj = SystemSettings(
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
            startup_grace_period_s=10,
            sensor_timeout_s=5,
            invalid_reading_threshold=5,
            data_retention_days=30,
        )
        db.add(settings_obj)
        db.commit()
        db.refresh(settings_obj)
    return settings_obj


@router.get("/{device_id}", response_model=SystemSettingsResponse)
def get_settings(device_id: str, db: Session = Depends(get_db)):
    """Retrieve system configuration settings for a device."""
    return _get_or_create_default_settings(db, device_id)


@router.put("/{device_id}", response_model=SystemSettingsResponse)
def update_settings(
    device_id: str,
    update_data: SystemSettingsUpdate,
    db: Session = Depends(get_db),
):
    """Update system settings with cross-field constraint validation."""
    settings_obj = _get_or_create_default_settings(db, device_id)

    # Calculate merged prospective values
    update_dict = update_data.model_dump(exclude_unset=True)

    prospective_empty = update_dict.get("empty_distance_cm", settings_obj.empty_distance_cm)
    prospective_full = update_dict.get("full_distance_cm", settings_obj.full_distance_cm)
    prospective_low = update_dict.get("low_level_threshold", settings_obj.low_level_threshold)
    prospective_high = update_dict.get("high_level_threshold", settings_obj.high_level_threshold)
    prospective_min_flow = update_dict.get("min_flow_lpm", settings_obj.min_flow_lpm)
    prospective_max_flow = update_dict.get("max_flow_lpm", settings_obj.max_flow_lpm)
    prospective_min_press = update_dict.get("min_pressure_bar", settings_obj.min_pressure_bar)
    prospective_max_press = update_dict.get("max_pressure_bar", settings_obj.max_pressure_bar)

    # Validate cross-field constraints
    if prospective_empty == prospective_full:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="empty_distance_cm cannot equal full_distance_cm",
        )
    if prospective_low >= prospective_high:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="low_level_threshold must be strictly less than high_level_threshold",
        )
    if prospective_min_flow >= prospective_max_flow:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="min_flow_lpm must be less than max_flow_lpm",
        )
    if prospective_min_press >= prospective_max_press:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="min_pressure_bar must be less than max_pressure_bar",
        )

    for key, value in update_dict.items():
        setattr(settings_obj, key, value)

    settings_obj.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(settings_obj)
    return settings_obj
