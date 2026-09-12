from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from backend.config import settings
from backend.database.store import Store
from backend.sensors.processor import validate_payload, trend, moisture_label
from backend.decision_engine.safety import IrrigationSafety
from backend.irrigation.controller import PumpController
from backend.alerts.service import evaluate_alerts
from backend.agent.farming_agent import answer

app = FastAPI(title="AGRI NEXA", version="0.1.0")
store, pump = Store(settings.database_url), PumpController(settings)
safety = IrrigationSafety(settings, store)

class ManualRequest(BaseModel):
    enabled: bool = True
    duration_seconds: int = Field(default=30, ge=1)
class AgentRequest(BaseModel):
    question: str = "What should I do today?"

def current():
    reading = store.latest()
    if reading: reading = {**reading, "pump_status": pump.running}
    return reading
def status():
    reading = current(); history = store.history()
    decision = safety.evaluate(reading).to_dict()
    moisture = reading.get("soil_moisture") if reading else None
    return {"mode": "MOCK" if settings.mock_mode else "REAL_HARDWARE", "online": bool(reading), "reading": reading,
            "water_status": moisture_label(moisture, settings.soil_moisture_threshold, settings.soil_moisture_sufficient),
            "moisture_trend": trend(history, "soil_moisture"), "irrigation": decision,
            "risk_level": decision["risk_level"], "optional_sensors": {k: (reading.get(k) if reading else None) for k in ["nitrogen","phosphorus","potassium","ph","ec","tds","water_level"]}}

@app.get("/api/health")
def health(): return {"ok": True, "mode": "mock" if settings.mock_mode else "real_hardware"}

@app.post("/api/sensors/ingest")
async def ingest(request: Request):
    """Accept device JSON directly, or the {"data": {...}} bridge envelope."""
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(422, "Sensor payload must be a JSON object")
    reading = validate_payload(payload.get("data", payload)).to_dict()
    if reading["pump_status"] is not None: pump.running = reading["pump_status"]
    store.add_reading(reading); alerts = evaluate_alerts(store, reading)
    return {"accepted": reading["valid"], "reading": reading, "new_alerts": alerts}

@app.get("/api/sensors/latest")
def latest():
    if not current(): raise HTTPException(404, "No sensor readings yet")
    return current()
@app.get("/api/sensors/history")
def history(limit: int = 50): return store.history(min(max(limit, 1), 500))
@app.get("/api/farm/status")
def farm_status(): return status()
@app.get("/api/irrigation/status")
def irrigation_status(): return {"pump_status": pump.running, "emergency_stop": safety.emergency, "decision": safety.evaluate(current()).to_dict()}

def start(mode: str, duration: int):
    decision = safety.evaluate(current(), mode, duration)
    now = datetime.now(timezone.utc).isoformat()
    if not decision.approved:
        store.log_irrigation(now, "IRRIGATION_BLOCKED", decision.reason, 0, mode, "blocked")
        return {"started": False, **decision.to_dict()}
    result = pump.command(True, decision.duration_seconds)
    store.log_irrigation(now, "IRRIGATION_STARTED" if result["ok"] else "IRRIGATION_FAILED", decision.reason, decision.duration_seconds, mode, "started" if result["ok"] else result["message"])
    return {"started": result["ok"], **decision.to_dict(), "actuator": result}

@app.post("/api/irrigation/automatic")
def automatic(): return start("automatic", settings.max_pump_runtime)
@app.post("/api/irrigation/manual")
def manual(request: ManualRequest):
    if not request.enabled:
        result = pump.command(False); store.log_irrigation(datetime.now(timezone.utc).isoformat(), "IRRIGATION_STOPPED", "manual_stop", 0, "manual", "stopped")
        return result
    return start("manual", request.duration_seconds)
@app.post("/api/irrigation/emergency-stop")
def emergency_stop():
    safety.emergency = True; result = pump.command(False)
    store.log_irrigation(datetime.now(timezone.utc).isoformat(), "IRRIGATION_STOPPED", "emergency_stop", 0, "emergency", "stopped")
    return {"emergency_stop": True, "actuator": result}
@app.post("/api/irrigation/reset-emergency")
def reset_emergency(): safety.emergency = False; return {"emergency_stop": False}
@app.get("/api/alerts")
def alerts(): return store.alerts()
@app.post("/api/agent/chat")
def chat(request: AgentRequest): return answer(request.question, current(), store.history(), safety.evaluate(current()).to_dict(), settings)
@app.get("/api/ai/predictions")
def predictions():
    state = status(); return {"prediction": state["water_status"], "confidence": 0.92 if state["online"] else 0, "note": "Rule-based local inference; LLM is not used for pump control."}

app.mount("/", StaticFiles(directory=Path(__file__).resolve().parents[2] / "frontend", html=True), name="dashboard")
