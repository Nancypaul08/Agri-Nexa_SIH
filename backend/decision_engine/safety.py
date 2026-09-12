from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from backend.config import Settings

@dataclass
class SafetyDecision:
    approved: bool; reason: str; duration_seconds: int = 0; risk_level: str = "low"
    def to_dict(self): return asdict(self)

class IrrigationSafety:
    def __init__(self, settings: Settings, store): self.settings, self.store, self.emergency = settings, store, False
    def evaluate(self, reading: dict | None, mode: str = "automatic", requested_duration: int | None = None) -> SafetyDecision:
        if self.emergency: return SafetyDecision(False, "Emergency stop is active", risk_level="critical")
        if not reading: return SafetyDecision(False, "No sensor data: fail-safe pump OFF", risk_level="critical")
        if not reading.get("valid", False): return SafetyDecision(False, "Invalid sensor data: fail-safe pump OFF", risk_level="critical")
        if reading.get("water_level") is not None and reading["water_level"] <= 0: return SafetyDecision(False, "Water tank is empty", risk_level="critical")
        if reading.get("pump_status") is True: return SafetyDecision(False, "Pump is already running", risk_level="medium")
        last = self.store.last_irrigation()
        if last:
            try:
                elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(last["timestamp"])).total_seconds()
                if elapsed < self.settings.pump_cooldown: return SafetyDecision(False, f"Pump cooldown active ({int(self.settings.pump_cooldown-elapsed)}s remaining)", risk_level="medium")
            except ValueError: pass
        soil = reading.get("soil_moisture")
        if soil is None: return SafetyDecision(False, "Soil moisture unavailable: fail-safe pump OFF", risk_level="critical")
        if mode == "automatic" and soil >= self.settings.soil_moisture_threshold: return SafetyDecision(False, "Soil moisture is not below irrigation threshold")
        duration = min(max(1, requested_duration or self.settings.max_pump_runtime), self.settings.max_pump_runtime)
        return SafetyDecision(True, "soil_moisture_low" if mode == "automatic" else "manual_request_safety_approved", duration, "high" if soil < self.settings.soil_moisture_threshold else "medium")
