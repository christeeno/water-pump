from datetime import datetime, timezone, timedelta
from app.models.telemetry import DeviceInfo


def test_device_active_and_stale_detection(client, db_session):
    now = datetime.now(timezone.utc)

    # 1. Active device (last_seen 10 seconds ago)
    active_device = DeviceInfo(
        device_id="active-controller-01",
        firmware_version="1.2.0",
        last_seen=now - timedelta(seconds=10),
        is_connected=True,
        controller_state="IDLE",
    )
    db_session.add(active_device)

    # 2. Stale device (last_seen 120 seconds ago > 60s threshold)
    stale_device = DeviceInfo(
        device_id="stale-controller-02",
        firmware_version="1.0.0",
        last_seen=now - timedelta(seconds=120),
        is_connected=True,
        controller_state="IDLE",
    )
    db_session.add(stale_device)
    db_session.commit()

    # Query active device
    res_active = client.get("/api/v1/devices/active-controller-01")
    assert res_active.status_code == 200
    assert res_active.json()["is_connected"] is True

    # Query stale device -> is_connected should be dynamically evaluated as False!
    res_stale = client.get("/api/v1/devices/stale-controller-02")
    assert res_stale.status_code == 200
    assert res_stale.json()["is_connected"] is False

    # List all devices
    res_list = client.get("/api/v1/devices")
    assert res_list.status_code == 200
    devices = {d["device_id"]: d["is_connected"] for d in res_list.json()}
    assert devices["active-controller-01"] is True
    assert devices["stale-controller-02"] is False


def test_device_not_found(client):
    response = client.get("/api/v1/devices/non-existent-device-xyz")
    assert response.status_code == 404
