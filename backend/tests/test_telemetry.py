from datetime import datetime, timezone


def test_valid_telemetry_ingestion(client, device_headers):
    payload = {
        "device_id": "esp32-water-controller-01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tank_distance_cm": 25.0,
        "tank_level_percent": 87.5,
        "flow_rate_lpm": 8.4,
        "pressure_bar": 1.6,
        "pump_current_a": 1.2,
        "pump_on": True,
        "mode": "AUTO",
        "controller_state": "FILLING",
        "sensor_status": {
            "ultrasonic": "OK",
            "flow": "OK",
            "pressure": "OK",
            "current": "OK",
        },
    }
    response = client.post("/api/v1/telemetry", json=payload, headers=device_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["device_id"] == "esp32-water-controller-01"
    assert data["validation"]["is_valid"] is True
    assert data["validation"]["status"] == "OK"
    assert "telemetry_id" in data


def test_missing_required_fields(client, device_headers):
    # Missing flow_rate_lpm, pressure_bar, etc.
    payload = {
        "device_id": "esp32-water-controller-01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tank_distance_cm": 25.0,
    }
    response = client.post("/api/v1/telemetry", json=payload, headers=device_headers)
    assert response.status_code == 422


def test_unauthenticated_request(client):
    payload = {
        "device_id": "esp32-water-controller-01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tank_distance_cm": 25.0,
        "tank_level_percent": 87.5,
        "flow_rate_lpm": 8.4,
        "pressure_bar": 1.6,
        "pump_current_a": 1.2,
        "pump_on": True,
        "mode": "AUTO",
        "controller_state": "FILLING",
        "sensor_status": {
            "ultrasonic": "OK",
            "flow": "OK",
            "pressure": "OK",
            "current": "OK",
        },
    }
    # No headers
    response = client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 401

    # Invalid header
    response = client.post("/api/v1/telemetry", json=payload, headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 401


def test_invalid_distance_values(client, device_headers):
    # Distance <= 0 or out of ultrasonic range
    payload = {
        "device_id": "esp32-water-controller-01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tank_distance_cm": -5.0,
        "tank_level_percent": 50.0,
        "flow_rate_lpm": 0.0,
        "pressure_bar": 0.5,
        "pump_current_a": 0.0,
        "pump_on": False,
        "mode": "AUTO",
        "controller_state": "IDLE",
        "sensor_status": {
            "ultrasonic": "OK",
            "flow": "OK",
            "pressure": "OK",
            "current": "OK",
        },
    }
    response = client.post("/api/v1/telemetry", json=payload, headers=device_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["validation"]["is_valid"] is False
    assert data["validation"]["raw_value"] == -5.0


def test_get_latest_and_history(client, device_headers):
    # Ingest record first
    payload = {
        "device_id": "test-device-get",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tank_distance_cm": 30.0,
        "tank_level_percent": 80.0,
        "flow_rate_lpm": 5.0,
        "pressure_bar": 1.2,
        "pump_current_a": 1.1,
        "pump_on": True,
        "mode": "AUTO",
        "controller_state": "FILLING",
        "sensor_status": {
            "ultrasonic": "OK",
            "flow": "OK",
            "pressure": "OK",
            "current": "OK",
        },
    }
    post_res = client.post("/api/v1/telemetry", json=payload, headers=device_headers)
    assert post_res.status_code == 200

    # Get latest
    latest_res = client.get("/api/v1/telemetry/latest?device_id=test-device-get")
    assert latest_res.status_code == 200
    latest_data = latest_res.json()
    assert latest_data["device_id"] == "test-device-get"
    assert latest_data["flow_rate_lpm"] == 5.0

    # Get history
    history_res = client.get("/api/v1/telemetry/history?device_id=test-device-get")
    assert history_res.status_code == 200
    history_data = history_res.json()
    assert len(history_data) >= 1
    assert history_data[0]["device_id"] == "test-device-get"
