import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Text,
)
from ..database import Base


def utcnow():
    return datetime.now(timezone.utc)


class TelemetryRecord(Base):
    __tablename__ = "telemetry_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_id = Column(String(64), index=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    tank_distance_cm = Column(Float, nullable=False)
    tank_level_percent = Column(Float, nullable=False)
    flow_rate_lpm = Column(Float, nullable=False)
    pressure_bar = Column(Float, nullable=False)
    pump_current_a = Column(Float, nullable=False)
    pump_on = Column(Boolean, nullable=False, default=False)
    mode = Column(String(32), nullable=False, default="AUTO")
    controller_state = Column(String(32), nullable=False, default="IDLE")
    sensor_status_json = Column(Text, nullable=False, default="{}")
    is_simulated = Column(Boolean, nullable=False, default=False)
    raw_tank_distance_cm = Column(Float, nullable=True)
    tank_level_valid = Column(Boolean, nullable=False, default=True)


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    event_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()), nullable=False)
    timestamp = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    severity = Column(String(16), nullable=False)  # INFO, WARNING, CRITICAL
    fault_category = Column(String(64), nullable=False)
    description = Column(String(255), nullable=False)
    sensor_evidence_json = Column(Text, nullable=False, default="{}")
    pump_state = Column(Boolean, nullable=False, default=False)
    recommended_action = Column(String(255), nullable=False)
    acknowledged = Column(Boolean, nullable=False, default=False, index=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    device_id = Column(String(64), index=True, nullable=False)


class DeviceInfo(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_id = Column(String(64), unique=True, index=True, nullable=False)
    firmware_version = Column(String(32), nullable=False, default="1.0.0")
    last_seen = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_telemetry_at = Column(DateTime(timezone=True), nullable=True)
    is_connected = Column(Boolean, nullable=False, default=True)
    controller_state = Column(String(32), nullable=False, default="IDLE")
    sensor_health_json = Column(Text, nullable=True, default="{}")
    api_key_hash = Column(String(128), nullable=True)


class PumpCommand(Base):
    __tablename__ = "pump_commands"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    command_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()), nullable=False)
    device_id = Column(String(64), index=True, nullable=False)
    command_type = Column(String(32), nullable=False)  # PUMP_ON, PUMP_OFF, SET_MODE_AUTO, SET_MODE_MANUAL
    issued_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    acknowledged = Column(Boolean, nullable=False, default=False, index=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    device_reported_state = Column(String(64), nullable=True)
    issued_by = Column(String(64), nullable=False, default="frontend")


class SystemSettings(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_id = Column(String(64), unique=True, index=True, nullable=False)
    tank_height_cm = Column(Float, nullable=False, default=100.0)
    empty_distance_cm = Column(Float, nullable=False, default=95.0)
    full_distance_cm = Column(Float, nullable=False, default=15.0)
    low_level_threshold = Column(Float, nullable=False, default=20.0)
    high_level_threshold = Column(Float, nullable=False, default=90.0)
    min_flow_lpm = Column(Float, nullable=False, default=0.5)
    max_flow_lpm = Column(Float, nullable=False, default=30.0)
    min_pressure_bar = Column(Float, nullable=False, default=0.5)
    max_pressure_bar = Column(Float, nullable=False, default=3.5)
    max_current_a = Column(Float, nullable=False, default=5.0)
    startup_grace_period_s = Column(Integer, nullable=False, default=10)
    sensor_timeout_s = Column(Integer, nullable=False, default=5)
    invalid_reading_threshold = Column(Integer, nullable=False, default=5)
    data_retention_days = Column(Integer, nullable=False, default=30)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
