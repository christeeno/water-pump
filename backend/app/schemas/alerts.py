import json
from datetime import datetime
from typing import Optional, Dict, Any, Union
from pydantic import BaseModel, ConfigDict, field_validator


class AlertEventResponse(BaseModel):
    id: int
    event_id: str
    timestamp: datetime
    severity: str
    fault_category: str
    description: str
    sensor_evidence_json: str
    sensor_evidence: Optional[Dict[str, Any]] = None
    pump_state: bool
    recommended_action: str
    acknowledged: bool
    acknowledged_at: Optional[datetime] = None
    device_id: str

    model_config = ConfigDict(from_attributes=True)

    @field_validator("sensor_evidence", mode="before")
    @classmethod
    def parse_sensor_evidence(cls, v, info):
        if v is not None:
            return v
        evidence_json = info.data.get("sensor_evidence_json")
        if evidence_json:
            try:
                return json.loads(evidence_json)
            except Exception:
                return {}
        return {}


class AlertAckResponse(BaseModel):
    success: bool = True
    event_id: str
    acknowledged: bool = True
    acknowledged_at: datetime
