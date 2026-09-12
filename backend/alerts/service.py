from datetime import datetime, timezone

def evaluate_alerts(store, reading: dict):
    alerts = []
    checks = [
        (reading.get("water_level") is not None and reading["water_level"] <= 0, "tank_empty", "critical", "Water tank empty — irrigation blocked"),
        (reading.get("valid") is False, "sensor_invalid", "warning", "Invalid sensor reading — pump is safely blocked"),
        (reading.get("soil_moisture") is not None and reading["soil_moisture"] < 20, "soil_critical", "warning", "Soil moisture critically low"),
    ]
    now = datetime.now(timezone.utc).isoformat()
    for triggered, key, severity, message in checks:
        if triggered and store.add_alert_once(now, key, severity, message): alerts.append(message)
    return alerts
