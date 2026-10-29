import json
from datetime import datetime
from typing import Optional, Dict, Any, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator


class SensorStatusSchema(BaseModel):
    ultrasonic: str = "OK"
    flow: str = "OK"
    pressure: str = "OK"
    current: str = "OK"

    model_config = ConfigDict(extra="allow")


class TelemetryCreate(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=64)
    timestamp: datetime
    tank_distance_cm: float
    tank_level_percent: Optional[float] = None
    flow_rate_lpm: float = Field(..., ge=0.0)
    pressure_bar: float = Field(..., ge=0.0)
    pump_current_a: float = Field(..., ge=0.0)
    pump_on: bool
    mode: str = "AUTO"
    controller_state: str = "IDLE"
    sensor_status: Union[SensorStatusSchema, Dict[str, str]] = Field(default_factory=SensorStatusSchema)

    @field_validator("sensor_status", mode="after")
    @classmethod
    def normalize_sensor_status(cls, v):
        if isinstance(v, SensorStatusSchema):
            return v.model_dump()
        return v


class SensorValidationSummary(BaseModel):
    raw_value: Optional[float] = None
    filtered_value: Optional[float] = None
    is_valid: bool
    status: str
    last_valid: Optional[float] = None
    is_stale: bool = False
    tank_level_percent: Optional[float] = None


class TelemetryIngestResponse(BaseModel):
    status: str = "success"
    device_id: str
    telemetry_id: int
    validation: SensorValidationSummary
    alerts_generated: int


class TelemetryResponse(BaseModel):
    id: int
    device_id: str
    timestamp: datetime
    tank_distance_cm: float
    tank_level_percent: float
    flow_rate_lpm: float
    pressure_bar: float
    pump_current_a: float
    pump_on: bool
    mode: str
    controller_state: str
    sensor_status_json: str
    sensor_status: Optional[Dict[str, Any]] = None
    is_simulated: bool
    raw_tank_distance_cm: Optional[float] = None
    tank_level_valid: bool

    model_config = ConfigDict(from_attributes=True)

    @field_validator("sensor_status", mode="before")
    @classmethod
    def populate_sensor_status(cls, v, info):
        # Allow reading from sensor_status_json if sensor_status is not set
        return v
