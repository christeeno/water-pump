import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union


def _extract_val(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _extract_sensor_status(sensor_status: Any) -> Dict[str, str]:
    if sensor_status is None:
        return {}
    if isinstance(sensor_status, dict):
        return sensor_status
    if isinstance(sensor_status, str):
        try:
            return json.loads(sensor_status)
        except Exception:
            return {"status": sensor_status}
    if hasattr(sensor_status, "model_dump"):
        return sensor_status.model_dump()
    return {}


def create_alert_dict(
    device_id: str,
    severity: str,
    fault_category: str,
    description: str,
    recommended_action: str,
    pump_state: bool,
    sensor_evidence: Dict[str, Any],
    timestamp: Optional[datetime] = None,
) -> Dict[str, Any]:
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    elif timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    return {
        "event_id": str(uuid.uuid4()),
        "timestamp": timestamp,
        "severity": severity,
        "fault_category": fault_category,
        "description": description,
        "sensor_evidence_json": json.dumps(sensor_evidence),
        "sensor_evidence": sensor_evidence,
        "pump_state": pump_state,
        "recommended_action": recommended_action,
        "acknowledged": False,
        "acknowledged_at": None,
        "device_id": device_id,
    }


def check_dry_running(telemetry: Any, settings: Any = None) -> Optional[Dict[str, Any]]:
    """Rule 1: pump ON, flow < 0.5 lpm after grace period -> CRITICAL."""
    pump_on = bool(_extract_val(telemetry, "pump_on", False))
    flow_rate = float(_extract_val(telemetry, "flow_rate_lpm", 0.0))
    min_flow = float(_extract_val(settings, "min_flow_lpm", 0.5)) if settings else 0.5
    device_id = str(_extract_val(telemetry, "device_id", "unknown"))

    if pump_on and flow_rate < min_flow:
        return create_alert_dict(
            device_id=device_id,
            severity="CRITICAL",
            fault_category="DRY_RUN",
            description="Possible dry-running detected: Pump is ON but water flow rate is below threshold.",
            recommended_action="Shut off pump immediately and inspect inflow water supply.",
            pump_state=True,
            sensor_evidence={
                "pump_on": True,
                "flow_rate_lpm": flow_rate,
                "threshold_lpm": min_flow,
            },
        )
    return None


def check_pipe_blockage(telemetry: Any, settings: Any = None) -> Optional[Dict[str, Any]]:
    """Rule 2: pressure > max AND flow < 1 lpm -> WARNING."""
    pressure = float(_extract_val(telemetry, "pressure_bar", 0.0))
    flow_rate = float(_extract_val(telemetry, "flow_rate_lpm", 0.0))
    max_pressure = float(_extract_val(settings, "max_pressure_bar", 3.5)) if settings else 3.5
    pump_on = bool(_extract_val(telemetry, "pump_on", False))
    device_id = str(_extract_val(telemetry, "device_id", "unknown"))

    if pressure > max_pressure and flow_rate < 1.0:
        return create_alert_dict(
            device_id=device_id,
            severity="WARNING",
            fault_category="PIPE_BLOCKAGE",
            description="Possible pipe blockage detected: Line pressure is abnormally high with restricted flow.",
            recommended_action="Inspect discharge valves and inspect distribution piping for obstructions.",
            pump_state=pump_on,
            sensor_evidence={
                "pressure_bar": pressure,
                "max_pressure_bar": max_pressure,
                "flow_rate_lpm": flow_rate,
            },
        )
    return None


def check_leakage(recent_telemetry: Any, settings: Any = None) -> Optional[Dict[str, Any]]:
    """Rule 3: level dropping while pump OFF -> WARNING."""
    if isinstance(recent_telemetry, (list, tuple)) and len(recent_telemetry) >= 2:
        first = recent_telemetry[0]
        last = recent_telemetry[-1]
        all_pump_off = all(not bool(_extract_val(r, "pump_on", False)) for r in recent_telemetry)
        first_level = float(_extract_val(first, "tank_level_percent", 0.0))
        last_level = float(_extract_val(last, "tank_level_percent", 0.0))
        device_id = str(_extract_val(last, "device_id", "unknown"))

        if all_pump_off and (first_level - last_level) >= 1.0:
            return create_alert_dict(
                device_id=device_id,
                severity="WARNING",
                fault_category="LEAKAGE",
                description="Possible leakage detected: Tank water level is declining while pump is inactive.",
                recommended_action="Check distribution network and plumbing connections for leaks.",
                pump_state=False,
                sensor_evidence={
                    "start_level_percent": first_level,
                    "end_level_percent": last_level,
                    "level_drop_percent": round(first_level - last_level, 2),
                },
            )
    elif recent_telemetry is not None and not isinstance(recent_telemetry, (list, tuple)):
        # Single record with drop attribute or flag
        level_drop = _extract_val(recent_telemetry, "level_drop_percent", None)
        pump_on = bool(_extract_val(recent_telemetry, "pump_on", False))
        if level_drop is not None and float(level_drop) >= 1.0 and not pump_on:
            device_id = str(_extract_val(recent_telemetry, "device_id", "unknown"))
            return create_alert_dict(
                device_id=device_id,
                severity="WARNING",
                fault_category="LEAKAGE",
                description="Possible leakage detected: Tank water level is declining while pump is inactive.",
                recommended_action="Check distribution network and plumbing connections for leaks.",
                pump_state=False,
                sensor_evidence={"level_drop_percent": float(level_drop)},
            )
    return None


def check_electrical_overload(telemetry: Any, settings: Any = None) -> Optional[Dict[str, Any]]:
    """Rule 4: current > max_current -> CRITICAL."""
    current = float(_extract_val(telemetry, "pump_current_a", 0.0))
    max_current = float(_extract_val(settings, "max_current_a", 5.0)) if settings else 5.0
    pump_on = bool(_extract_val(telemetry, "pump_on", False))
    device_id = str(_extract_val(telemetry, "device_id", "unknown"))

    if current > max_current:
        return create_alert_dict(
            device_id=device_id,
            severity="CRITICAL",
            fault_category="ELECTRICAL_OVERLOAD",
            description="Possible electrical overload detected: Motor current draw exceeds safety limit.",
            recommended_action="Disconnect pump power immediately and inspect motor winding and impeller.",
            pump_state=pump_on,
            sensor_evidence={
                "pump_current_a": current,
                "max_current_a": max_current,
            },
        )
    return None


def check_low_source_water(telemetry: Any, settings: Any = None) -> Optional[Dict[str, Any]]:
    """Rule 5: placeholder, INFO."""
    source_water_low = bool(_extract_val(telemetry, "source_water_low", False))
    controller_state = str(_extract_val(telemetry, "controller_state", ""))
    device_id = str(_extract_val(telemetry, "device_id", "unknown"))
    pump_on = bool(_extract_val(telemetry, "pump_on", False))

    if source_water_low or controller_state in ["SOURCE_EMPTY", "LOW_SOURCE"]:
        return create_alert_dict(
            device_id=device_id,
            severity="INFO",
            fault_category="LOW_SOURCE_WATER",
            description="Possible low source water: Intake reservoir water level is near depletion.",
            recommended_action="Verify source water replenishment before scheduling next pumping cycle.",
            pump_state=pump_on,
            sensor_evidence={"controller_state": controller_state},
        )
    return None


def check_tank_overflow_risk(telemetry: Any, settings: Any = None) -> Optional[Dict[str, Any]]:
    """Rule 6: level >= 95% while pump ON -> CRITICAL."""
    level = float(_extract_val(telemetry, "tank_level_percent", 0.0))
    pump_on = bool(_extract_val(telemetry, "pump_on", False))
    device_id = str(_extract_val(telemetry, "device_id", "unknown"))

    if pump_on and level >= 95.0:
        return create_alert_dict(
            device_id=device_id,
            severity="CRITICAL",
            fault_category="TANK_OVERFLOW",
            description="Possible tank overflow risk: Water level reached dangerous high threshold while pump is running.",
            recommended_action="Cut off pump immediately to prevent liquid overflow.",
            pump_state=True,
            sensor_evidence={
                "tank_level_percent": level,
                "pump_on": True,
                "critical_threshold": 95.0,
            },
        )
    return None


def check_ultrasonic_failure(telemetry: Any, sensor_status: Any) -> Optional[Dict[str, Any]]:
    """Rule 7: ultrasonic != OK -> WARNING/CRITICAL."""
    status_map = _extract_sensor_status(sensor_status)
    status = status_map.get("ultrasonic", "OK").upper()
    device_id = str(_extract_val(telemetry, "device_id", "unknown"))
    pump_on = bool(_extract_val(telemetry, "pump_on", False))

    if status != "OK":
        severity = "CRITICAL" if status in ["OFFLINE", "ERROR", "TIMEOUT", "FAILED"] else "WARNING"
        return create_alert_dict(
            device_id=device_id,
            severity=severity,
            fault_category="ULTRASONIC_SENSOR_FAILURE",
            description="Ultrasonic sensor failure: Echo sensor reported abnormal or offline state.",
            recommended_action="Inspect ultrasonic sensor wiring, cleanliness of transducer, and alignment.",
            pump_state=pump_on,
            sensor_evidence={"ultrasonic_status": status},
        )
    return None


def check_pressure_sensor_failure(telemetry: Any, sensor_status: Any) -> Optional[Dict[str, Any]]:
    """Rule 8: pressure != OK -> WARNING."""
    status_map = _extract_sensor_status(sensor_status)
    status = status_map.get("pressure", "OK").upper()
    device_id = str(_extract_val(telemetry, "device_id", "unknown"))
    pump_on = bool(_extract_val(telemetry, "pump_on", False))

    if status != "OK":
        return create_alert_dict(
            device_id=device_id,
            severity="WARNING",
            fault_category="PRESSURE_SENSOR_FAILURE",
            description="Pressure sensor failure: Transducer loop broken or reading out of calibration.",
            recommended_action="Inspect pressure transducer cable and calibrate sensor input.",
            pump_state=pump_on,
            sensor_evidence={"pressure_status": status},
        )
    return None


def check_current_sensor_failure(telemetry: Any, sensor_status: Any) -> Optional[Dict[str, Any]]:
    """Rule 9: current != OK -> WARNING."""
    status_map = _extract_sensor_status(sensor_status)
    status = status_map.get("current", "OK").upper()
    device_id = str(_extract_val(telemetry, "device_id", "unknown"))
    pump_on = bool(_extract_val(telemetry, "pump_on", False))

    if status != "OK":
        return create_alert_dict(
            device_id=device_id,
            severity="WARNING",
            fault_category="CURRENT_SENSOR_FAILURE",
            description="Current sensor failure: Current transformer disconnected or signal saturated.",
            recommended_action="Inspect CT clamp wiring and burden resistor connection.",
            pump_state=pump_on,
            sensor_evidence={"current_status": status},
        )
    return None


def check_flow_sensor_failure(telemetry: Any, sensor_status: Any) -> Optional[Dict[str, Any]]:
    """Rule 10: flow != OK -> WARNING."""
    status_map = _extract_sensor_status(sensor_status)
    status = status_map.get("flow", "OK").upper()
    device_id = str(_extract_val(telemetry, "device_id", "unknown"))
    pump_on = bool(_extract_val(telemetry, "pump_on", False))

    if status != "OK":
        return create_alert_dict(
            device_id=device_id,
            severity="WARNING",
            fault_category="FLOW_SENSOR_FAILURE",
            description="Flow sensor failure: Pulse signal missing or meter rotor jammed.",
            recommended_action="Inspect turbine flow meter mechanism and signal wiring.",
            pump_state=pump_on,
            sensor_evidence={"flow_status": status},
        )
    return None


def evaluate_all_faults(
    telemetry: Any,
    settings: Any = None,
    recent_telemetry: Optional[List[Any]] = None,
) -> List[Dict[str, Any]]:
    """Run all 10 fault rules and return list of generated AlertEvent dicts."""
    alerts: List[Dict[str, Any]] = []

    # Extract sensor status
    sensor_status = _extract_val(telemetry, "sensor_status", None)
    if not sensor_status:
        sensor_status_json = _extract_val(telemetry, "sensor_status_json", None)
        sensor_status = _extract_sensor_status(sensor_status_json)

    # Rule 1: Dry Running
    r1 = check_dry_running(telemetry, settings)
    if r1:
        alerts.append(r1)

    # Rule 2: Pipe Blockage
    r2 = check_pipe_blockage(telemetry, settings)
    if r2:
        alerts.append(r2)

    # Rule 3: Leakage
    r3 = check_leakage(recent_telemetry or telemetry, settings)
    if r3:
        alerts.append(r3)

    # Rule 4: Electrical Overload
    r4 = check_electrical_overload(telemetry, settings)
    if r4:
        alerts.append(r4)

    # Rule 5: Low Source Water
    r5 = check_low_source_water(telemetry, settings)
    if r5:
        alerts.append(r5)

    # Rule 6: Tank Overflow Risk
    r6 = check_tank_overflow_risk(telemetry, settings)
    if r6:
        alerts.append(r6)

    # Rule 7: Ultrasonic Failure
    r7 = check_ultrasonic_failure(telemetry, sensor_status)
    if r7:
        alerts.append(r7)

    # Rule 8: Pressure Sensor Failure
    r8 = check_pressure_sensor_failure(telemetry, sensor_status)
    if r8:
        alerts.append(r8)

    # Rule 9: Current Sensor Failure
    r9 = check_current_sensor_failure(telemetry, sensor_status)
    if r9:
        alerts.append(r9)

    # Rule 10: Flow Sensor Failure
    r10 = check_flow_sensor_failure(telemetry, sensor_status)
    if r10:
        alerts.append(r10)

    return alerts
