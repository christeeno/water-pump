from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class SystemSettingsBase(BaseModel):
    tank_height_cm: float = Field(100.0, gt=0, description="Tank total height in cm")
    empty_distance_cm: float = Field(95.0, gt=0, description="Sensor distance when empty")
    full_distance_cm: float = Field(15.0, gt=0, description="Sensor distance when full")
    low_level_threshold: float = Field(20.0, gt=0, le=100.0, description="Low level alarm/trigger threshold (%)")
    high_level_threshold: float = Field(90.0, gt=0, le=100.0, description="High level stop threshold (%)")
    min_flow_lpm: float = Field(0.5, ge=0, description="Minimum flow rate threshold")
    max_flow_lpm: float = Field(30.0, gt=0, description="Maximum flow rate threshold")
    min_pressure_bar: float = Field(0.5, ge=0, description="Minimum line pressure")
    max_pressure_bar: float = Field(3.5, gt=0, description="Maximum safe line pressure")
    max_current_a: float = Field(5.0, gt=0, description="Maximum safe motor current")
    startup_grace_period_s: int = Field(10, ge=0, description="Grace period before dry-run check")
    sensor_timeout_s: int = Field(5, gt=0, description="Timeout for sensor readings")
    invalid_reading_threshold: int = Field(5, gt=0, description="Max consecutive bad readings")
    data_retention_days: int = Field(30, gt=0, description="Days to retain historical telemetry")

    @model_validator(mode="after")
    def validate_rules(self):
        if self.empty_distance_cm == self.full_distance_cm:
            raise ValueError("empty_distance_cm cannot equal full_distance_cm")
        if self.low_level_threshold >= self.high_level_threshold:
            raise ValueError("low_level_threshold must be strictly less than high_level_threshold")
        if self.min_flow_lpm >= self.max_flow_lpm:
            raise ValueError("min_flow_lpm must be less than max_flow_lpm")
        if self.min_pressure_bar >= self.max_pressure_bar:
            raise ValueError("min_pressure_bar must be less than max_pressure_bar")
        return self


class SystemSettingsCreate(SystemSettingsBase):
    device_id: str = Field(..., min_length=1, max_length=64)


class SystemSettingsUpdate(BaseModel):
    tank_height_cm: Optional[float] = Field(None, gt=0)
    empty_distance_cm: Optional[float] = Field(None, gt=0)
    full_distance_cm: Optional[float] = Field(None, gt=0)
    low_level_threshold: Optional[float] = Field(None, gt=0, le=100.0)
    high_level_threshold: Optional[float] = Field(None, gt=0, le=100.0)
    min_flow_lpm: Optional[float] = Field(None, ge=0)
    max_flow_lpm: Optional[float] = Field(None, gt=0)
    min_pressure_bar: Optional[float] = Field(None, ge=0)
    max_pressure_bar: Optional[float] = Field(None, gt=0)
    max_current_a: Optional[float] = Field(None, gt=0)
    startup_grace_period_s: Optional[int] = Field(None, ge=0)
    sensor_timeout_s: Optional[int] = Field(None, gt=0)
    invalid_reading_threshold: Optional[int] = Field(None, gt=0)
    data_retention_days: Optional[int] = Field(None, gt=0)

    @model_validator(mode="after")
    def validate_update(self):
        if self.empty_distance_cm is not None and self.full_distance_cm is not None:
            if self.empty_distance_cm == self.full_distance_cm:
                raise ValueError("empty_distance_cm cannot equal full_distance_cm")
        if self.low_level_threshold is not None and self.high_level_threshold is not None:
            if self.low_level_threshold >= self.high_level_threshold:
                raise ValueError("low_level_threshold must be strictly less than high_level_threshold")
        return self


class SystemSettingsResponse(SystemSettingsBase):
    id: int
    device_id: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
