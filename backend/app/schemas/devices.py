from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, field_validator
import json


class DeviceInfoResponse(BaseModel):
    id: int
    device_id: str
    firmware_version: str
    last_seen: datetime
    last_telemetry_at: Optional[datetime] = None
    is_connected: bool
    controller_state: str
    sensor_health_json: Optional[str] = "{}"
    sensor_health: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("sensor_health", mode="before")
    @classmethod
    def parse_sensor_health(cls, v, info):
        if v is not None:
            return v
        health_json = info.data.get("sensor_health_json")
        if health_json:
            try:
                return json.loads(health_json)
            except Exception:
                return {}
        return {}
