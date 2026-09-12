from backend.sensors.processor import moisture_label, trend

def answer(question: str, reading: dict | None, history: list[dict], decision: dict, settings) -> dict:
    if not reading:
        return {"current_status": "No live field data", "reason": "No valid sensor reading has reached AGRI NEXA.", "recommended_action": "Check the device connection.", "system_action": "Pump remains OFF for safety.", "confidence": 0, "data_used": ["sensor availability"]}
    moisture = reading.get("soil_moisture"); status = moisture_label(moisture, settings.soil_moisture_threshold, settings.soil_moisture_sufficient)
    falling = trend(history, "soil_moisture") == "falling"
    if not reading.get("valid"):
        current, reason, confidence = "Sensor data needs attention", "; ".join(reading.get("errors") or ["Reading failed validation"]), 90
    elif status == "dry":
        current = "⚠️ Water stress likely"; reason = f"Soil moisture is {moisture:.0f}%, below the {settings.soil_moisture_threshold:.0f}% irrigation threshold" + (" and has been falling" if falling else "") + "."; confidence = 92
    elif status == "sufficient":
        current, reason, confidence = "✅ Soil moisture is sufficient", f"Soil moisture is {moisture:.0f}%, above the sufficient range.", 94
    else:
        current, reason, confidence = "✅ Field moisture is acceptable", f"Soil moisture is {moisture:.0f}%.", 86
    nutrient = "NPK data is unavailable; no nutrient conclusion is made."
    if reading.get("nitrogen") is not None: nutrient = "NPK is available but needs crop-stage reference calibration before diagnosing deficiency."
    if reading.get("pump_status"):
        action, system_action = "Irrigation is already running; monitor soil moisture.", "Pump is ON through the relay and will stop at the configured maximum runtime."
    elif decision["approved"]:
        action, system_action = "Irrigate now.", "Pump may be started through safety controls."
    else:
        action, system_action = "Do not irrigate yet; " + decision["reason"] + ".", "Pump remains OFF."
    return {"current_status": current, "reason": reason, "recommended_action": action, "system_action": system_action, "confidence": confidence, "data_used": ["soil moisture", "temperature", "humidity", "recent trend", nutrient], "answer_to": question}
