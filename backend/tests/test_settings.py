def test_get_settings_default(client):
    device_id = "test-settings-dev-01"
    response = client.get(f"/api/v1/settings/{device_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["device_id"] == device_id
    assert data["tank_height_cm"] == 100.0
    assert data["empty_distance_cm"] == 95.0
    assert data["full_distance_cm"] == 15.0
    assert data["low_level_threshold"] == 20.0
    assert data["high_level_threshold"] == 90.0


def test_valid_settings_update(client):
    device_id = "test-settings-dev-02"
    update_payload = {
        "empty_distance_cm": 120.0,
        "full_distance_cm": 20.0,
        "low_level_threshold": 25.0,
        "high_level_threshold": 85.0,
        "max_flow_lpm": 35.0,
    }

    response = client.put(f"/api/v1/settings/{device_id}", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["empty_distance_cm"] == 120.0
    assert data["full_distance_cm"] == 20.0
    assert data["low_level_threshold"] == 25.0
    assert data["high_level_threshold"] == 85.0
    assert data["max_flow_lpm"] == 35.0


def test_invalid_settings_equal_empty_full_distance(client):
    device_id = "test-settings-dev-03"
    # Setting empty == full distance
    invalid_payload = {
        "empty_distance_cm": 50.0,
        "full_distance_cm": 50.0,
    }
    response = client.put(f"/api/v1/settings/{device_id}", json=invalid_payload)
    assert response.status_code == 422
    assert "empty_distance_cm cannot equal full_distance_cm" in str(response.json())


def test_invalid_threshold_ordering(client):
    device_id = "test-settings-dev-04"
    # Setting low threshold >= high threshold
    invalid_payload = {
        "low_level_threshold": 80.0,
        "high_level_threshold": 70.0,
    }
    response = client.put(f"/api/v1/settings/{device_id}", json=invalid_payload)
    assert response.status_code == 422
    assert "low_level_threshold must be strictly less than high_level_threshold" in str(response.json())
