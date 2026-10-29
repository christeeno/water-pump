def test_health_endpoint(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert "simulation_mode" in data
    assert "timestamp" in data


def test_websocket_dashboard(client):
    with client.websocket_connect("/ws/dashboard") as websocket:
        # Upon connect, dashboard receives initial state if available
        # send a text frame to ensure connection functions properly
        websocket.send_text("ping")
