from fastapi.testclient import TestClient
from backend.api.main import app


client = TestClient(app)


def test_dashboard_and_health_are_served():
    assert client.get("/").status_code == 200
    assert client.get("/api/health").json()["ok"] is True


def test_direct_sensor_payload_is_accepted():
    response = client.post("/api/sensors/ingest", json={
        "soil_moisture": 42, "temperature": 29, "humidity": 67,
        "pump_status": False, "water_level": 70,
    })
    assert response.status_code == 200
    assert response.json()["accepted"] is True


def test_invalid_sensor_payload_is_safely_rejected():
    response = client.post("/api/sensors/ingest", json={"soil_moisture": 150})
    assert response.status_code == 200
    assert response.json()["accepted"] is False
