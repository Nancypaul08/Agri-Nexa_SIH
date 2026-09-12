from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any

@dataclass
class SensorReading:
    soil_moisture: float | None = None; temperature: float | None = None; humidity: float | None = None; pump_status: bool | None = None
    water_level: float | None = None; nitrogen: float | None = None; phosphorus: float | None = None; potassium: float | None = None
    ph: float | None = None; ec: float | None = None; tds: float | None = None; timestamp: str = ""; valid: bool = True; errors: list[str] | None = None
    def to_dict(self) -> dict[str, Any]: return asdict(self)

RANGES = {"soil_moisture": (0, 100), "temperature": (-20, 70), "humidity": (0, 100), "water_level": (0, 100), "ph": (0, 14), "ec": (0, 20), "tds": (0, 5000), "nitrogen": (0, 1000), "phosphorus": (0, 1000), "potassium": (0, 1000)}

def validate_payload(payload: dict[str, Any]) -> SensorReading:
    errors: list[str] = []; values: dict[str, Any] = {}
    for name, (low, high) in RANGES.items():
        raw = payload.get(name)
        if raw is None or raw == "": values[name] = None; continue
        try:
            value = float(raw)
            if not low <= value <= high: errors.append(f"{name} outside plausible range ({low}-{high})")
            values[name] = value
        except (TypeError, ValueError): values[name] = None; errors.append(f"{name} is not numeric")
    pump = payload.get("pump_status")
    if pump is not None and not isinstance(pump, bool): errors.append("pump_status is not boolean"); pump = None
    return SensorReading(**values, pump_status=pump, timestamp=payload.get("timestamp") or datetime.now(timezone.utc).isoformat(), valid=not errors, errors=errors)

def moisture_label(value: float | None, dry: float, sufficient: float) -> str:
    if value is None: return "unknown"
    if value < dry: return "dry"
    if value > sufficient: return "sufficient"
    return "acceptable"

def trend(readings: list[dict[str, Any]], field: str) -> str:
    vals = [r.get(field) for r in readings if r.get(field) is not None]
    if len(vals) < 2: return "unknown"
    delta = vals[-1] - vals[0]
    return "stable" if abs(delta) < 1 else ("rising" if delta > 0 else "falling")
