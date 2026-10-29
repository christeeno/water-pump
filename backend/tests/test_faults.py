from app.services.fault_detection import (
    check_dry_running,
    check_pipe_blockage,
    check_leakage,
    check_electrical_overload,
    check_tank_overflow_risk,
    check_ultrasonic_failure,
    check_pressure_sensor_failure,
    check_current_sensor_failure,
    check_flow_sensor_failure,
    evaluate_all_faults,
)


def test_dry_running_detection():
    # Pump ON, flow < 0.5 lpm
    telemetry = {
        "device_id": "test-dev-01",
        "pump_on": True,
        "flow_rate_lpm": 0.2,
    }
    settings = {"min_flow_lpm": 0.5}

    alert = check_dry_running(telemetry, settings)
    assert alert is not None
    assert alert["severity"] == "CRITICAL"
    assert alert["fault_category"] == "DRY_RUN"
    assert "Possible dry-running" in alert["description"]
    assert alert["pump_state"] is True

    # Pump ON, flow normal -> No alert
    normal_telemetry = {
        "device_id": "test-dev-01",
        "pump_on": True,
        "flow_rate_lpm": 5.0,
    }
    assert check_dry_running(normal_telemetry, settings) is None

    # Pump OFF, flow 0 -> No dry-run alert
    off_telemetry = {
        "device_id": "test-dev-01",
        "pump_on": False,
        "flow_rate_lpm": 0.0,
    }
    assert check_dry_running(off_telemetry, settings) is None


def test_electrical_overload_detection():
    # Current > max_current (5.0A)
    telemetry = {
        "device_id": "test-dev-01",
        "pump_on": True,
        "pump_current_a": 6.8,
    }
    settings = {"max_current_a": 5.0}

    alert = check_electrical_overload(telemetry, settings)
    assert alert is not None
    assert alert["severity"] == "CRITICAL"
    assert alert["fault_category"] == "ELECTRICAL_OVERLOAD"
    assert "Possible electrical overload" in alert["description"]

    # Normal current
    telemetry["pump_current_a"] = 2.1
    assert check_electrical_overload(telemetry, settings) is None


def test_tank_overflow_detection():
    # Level >= 95% while pump is ON
    telemetry = {
        "device_id": "test-dev-01",
        "pump_on": True,
        "tank_level_percent": 96.5,
    }
    alert = check_tank_overflow_risk(telemetry)
    assert alert is not None
    assert alert["severity"] == "CRITICAL"
    assert alert["fault_category"] == "TANK_OVERFLOW"
    assert "Possible tank overflow risk" in alert["description"]

    # Level 96% while pump is OFF -> No overflow risk alert
    telemetry["pump_on"] = False
    assert check_tank_overflow_risk(telemetry) is None

    # Level 80% while pump is ON -> No alert
    telemetry["pump_on"] = True
    telemetry["tank_level_percent"] = 80.0
    assert check_tank_overflow_risk(telemetry) is None


def test_ultrasonic_failure_detection():
    # Ultrasonic OFFLINE -> CRITICAL
    telemetry = {"device_id": "test-dev-01", "pump_on": False}
    alert = check_ultrasonic_failure(telemetry, {"ultrasonic": "OFFLINE"})
    assert alert is not None
    assert alert["severity"] == "CRITICAL"
    assert alert["fault_category"] == "ULTRASONIC_SENSOR_FAILURE"
    assert "Ultrasonic sensor failure" in alert["description"]
    # Sensor failure should not say "Possible"
    assert not alert["description"].startswith("Possible")

    # Ultrasonic DEGRADED -> WARNING
    alert_degraded = check_ultrasonic_failure(telemetry, {"ultrasonic": "DEGRADED"})
    assert alert_degraded is not None
    assert alert_degraded["severity"] == "WARNING"

    # Ultrasonic OK -> None
    assert check_ultrasonic_failure(telemetry, {"ultrasonic": "OK"}) is None


def test_pipe_blockage_detection():
    # Pressure > max (3.5) and flow < 1.0 lpm
    telemetry = {
        "device_id": "test-dev-01",
        "pressure_bar": 4.0,
        "flow_rate_lpm": 0.5,
        "pump_on": True,
    }
    settings = {"max_pressure_bar": 3.5}
    alert = check_pipe_blockage(telemetry, settings)
    assert alert is not None
    assert alert["severity"] == "WARNING"
    assert alert["fault_category"] == "PIPE_BLOCKAGE"
    assert "Possible pipe blockage" in alert["description"]


def test_leakage_detection():
    recent = [
        {"device_id": "test-dev-01", "pump_on": False, "tank_level_percent": 80.0},
        {"device_id": "test-dev-01", "pump_on": False, "tank_level_percent": 77.0},
    ]
    alert = check_leakage(recent)
    assert alert is not None
    assert alert["severity"] == "WARNING"
    assert alert["fault_category"] == "LEAKAGE"
    assert "Possible leakage" in alert["description"]


def test_other_sensor_failures():
    telemetry = {"device_id": "test-dev-01", "pump_on": True}

    # Pressure
    p_alert = check_pressure_sensor_failure(telemetry, {"pressure": "ERROR"})
    assert p_alert is not None
    assert p_alert["fault_category"] == "PRESSURE_SENSOR_FAILURE"
    assert not p_alert["description"].startswith("Possible")

    # Current
    c_alert = check_current_sensor_failure(telemetry, {"current": "DISCONNECTED"})
    assert c_alert is not None
    assert c_alert["fault_category"] == "CURRENT_SENSOR_FAILURE"

    # Flow
    f_alert = check_flow_sensor_failure(telemetry, {"flow": "NO_PULSE"})
    assert f_alert is not None
    assert f_alert["fault_category"] == "FLOW_SENSOR_FAILURE"


def test_evaluate_all_faults_comprehensive():
    # Clean telemetry
    clean_telemetry = {
        "device_id": "test-dev-01",
        "pump_on": True,
        "flow_rate_lpm": 10.0,
        "pressure_bar": 2.0,
        "pump_current_a": 2.0,
        "tank_level_percent": 50.0,
        "sensor_status": {
            "ultrasonic": "OK",
            "flow": "OK",
            "pressure": "OK",
            "current": "OK",
        },
    }
    alerts = evaluate_all_faults(clean_telemetry)
    assert len(alerts) == 0

    # Faulty telemetry: dry running + electrical overload
    faulty_telemetry = {
        "device_id": "test-dev-01",
        "pump_on": True,
        "flow_rate_lpm": 0.1,
        "pressure_bar": 2.0,
        "pump_current_a": 7.5,
        "tank_level_percent": 50.0,
        "sensor_status": {
            "ultrasonic": "OK",
            "flow": "OK",
            "pressure": "OK",
            "current": "OK",
        },
    }
    alerts = evaluate_all_faults(faulty_telemetry)
    assert len(alerts) == 2
    categories = [a["fault_category"] for a in alerts]
    assert "DRY_RUN" in categories
    assert "ELECTRICAL_OVERLOAD" in categories
