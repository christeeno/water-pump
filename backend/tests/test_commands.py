from datetime import datetime, timezone, timedelta
from app.models.telemetry import PumpCommand


def test_command_creation(client, frontend_headers):
    device_id = "test-cmd-device-01"
    payload = {"command_type": "PUMP_ON"}

    response = client.post(
        f"/api/v1/devices/{device_id}/commands",
        json=payload,
        headers=frontend_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["device_id"] == device_id
    assert data["command_type"] == "PUMP_ON"
    assert data["acknowledged"] is False
    assert "command_id" in data
    assert "expires_at" in data


def test_command_acknowledgement(client, frontend_headers, device_headers):
    device_id = "test-cmd-device-02"

    # 1. Frontend creates command
    create_res = client.post(
        f"/api/v1/devices/{device_id}/commands",
        json={"command_type": "PUMP_ON"},
        headers=frontend_headers,
    )
    assert create_res.status_code == 201
    cmd_data = create_res.json()
    command_id = cmd_data["command_id"]

    # 2. Device polls pending commands
    pending_res = client.get(
        f"/api/v1/devices/{device_id}/commands/pending",
        headers=device_headers,
    )
    assert pending_res.status_code == 200
    pending_list = pending_res.json()
    assert len(pending_list) == 1
    assert pending_list[0]["command_id"] == command_id

    # 3. Device acknowledges command
    ack_res = client.post(
        f"/api/v1/devices/{device_id}/commands/{command_id}/ack",
        json={"device_reported_state": "PUMPING"},
        headers=device_headers,
    )
    assert ack_res.status_code == 200
    ack_data = ack_res.json()
    assert ack_data["acknowledged"] is True
    assert ack_data["device_reported_state"] == "PUMPING"
    assert ack_data["acknowledged_at"] is not None

    # 4. Device checks pending commands again (should now be empty)
    pending_res2 = client.get(
        f"/api/v1/devices/{device_id}/commands/pending",
        headers=device_headers,
    )
    assert len(pending_res2.json()) == 0


def test_duplicate_command_protection(client, frontend_headers):
    device_id = "test-cmd-device-03"

    # Issue first command
    res1 = client.post(
        f"/api/v1/devices/{device_id}/commands",
        json={"command_type": "SET_MODE_AUTO"},
        headers=frontend_headers,
    )
    assert res1.status_code == 201

    # Issue duplicate pending command of same type -> Should be rejected with 409 Conflict
    res2 = client.post(
        f"/api/v1/devices/{device_id}/commands",
        json={"command_type": "SET_MODE_AUTO"},
        headers=frontend_headers,
    )
    assert res2.status_code == 409
    assert "Duplicate command" in res2.json()["detail"]


def test_expired_command_handling(client, frontend_headers, device_headers, db_session):
    device_id = "test-cmd-device-04"

    # Directly inject an already expired command into the database
    now = datetime.now(timezone.utc)
    expired_cmd = PumpCommand(
        device_id=device_id,
        command_type="PUMP_OFF",
        issued_at=now - timedelta(seconds=120),
        expires_at=now - timedelta(seconds=60),
        acknowledged=False,
        issued_by="frontend",
    )
    db_session.add(expired_cmd)
    db_session.commit()
    db_session.refresh(expired_cmd)

    # 1. Device queries pending commands -> Expired command should be excluded
    pending_res = client.get(
        f"/api/v1/devices/{device_id}/commands/pending",
        headers=device_headers,
    )
    assert pending_res.status_code == 200
    pending_ids = [c["command_id"] for c in pending_res.json()]
    assert expired_cmd.command_id not in pending_ids

    # 2. Attempting to acknowledge an expired command should fail with 400 Bad Request
    ack_res = client.post(
        f"/api/v1/devices/{device_id}/commands/{expired_cmd.command_id}/ack",
        json={"device_reported_state": "IDLE"},
        headers=device_headers,
    )
    assert ack_res.status_code == 400
    assert "already expired" in ack_res.json()["detail"]
