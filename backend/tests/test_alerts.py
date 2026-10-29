from datetime import datetime, timezone
from app.models.telemetry import AlertEvent


def test_alerts_list_and_ack(client, db_session):
    now = datetime.now(timezone.utc)
    alert = AlertEvent(
        event_id="alert-uuid-test-01",
        timestamp=now,
        severity="CRITICAL",
        fault_category="DRY_RUN",
        description="Possible dry-running detected",
        sensor_evidence_json='{"flow_rate_lpm": 0.1}',
        pump_state=True,
        recommended_action="Shut off pump",
        acknowledged=False,
        device_id="dev-alert-test",
    )
    db_session.add(alert)
    db_session.commit()

    # 1. Query all alerts
    res = client.get("/api/v1/alerts")
    assert res.status_code == 200
    alerts = res.json()
    assert len(alerts) >= 1
    target = next((a for a in alerts if a["event_id"] == "alert-uuid-test-01"), None)
    assert target is not None
    assert target["acknowledged"] is False
    assert target["sensor_evidence"]["flow_rate_lpm"] == 0.1

    # 2. Filter by severity
    res_crit = client.get("/api/v1/alerts?severity=CRITICAL")
    assert res_crit.status_code == 200
    assert any(a["event_id"] == "alert-uuid-test-01" for a in res_crit.json())

    # 3. Filter by non-matching severity
    res_info = client.get("/api/v1/alerts?severity=INFO")
    assert res_info.status_code == 200
    assert not any(a["event_id"] == "alert-uuid-test-01" for a in res_info.json())

    # 4. Acknowledge alert
    ack_res = client.post("/api/v1/alerts/alert-uuid-test-01/ack")
    assert ack_res.status_code == 200
    assert ack_res.json()["acknowledged"] is True

    # 5. Check acknowledged status filter
    res_unack = client.get("/api/v1/alerts?acknowledged=false")
    assert not any(a["event_id"] == "alert-uuid-test-01" for a in res_unack.json())

    res_ack = client.get("/api/v1/alerts?acknowledged=true")
    assert any(a["event_id"] == "alert-uuid-test-01" for a in res_ack.json())
