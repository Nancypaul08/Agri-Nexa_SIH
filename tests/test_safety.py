from pathlib import Path
from backend.config import Settings
from backend.database.store import Store
from backend.decision_engine.safety import IrrigationSafety

def safety(tmp_path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'test.db'}", pump_cooldown=300)
    return IrrigationSafety(settings, Store(settings.database_url))
def reading(**overrides):
    r = {"valid": True, "soil_moisture": 24, "water_level": 80, "pump_status": False}
    r.update(overrides); return r
def test_dry_soil_approved(tmp_path): assert safety(tmp_path).evaluate(reading()).approved
def test_wet_soil_blocked(tmp_path): assert not safety(tmp_path).evaluate(reading(soil_moisture=55)).approved
def test_invalid_data_fails_closed(tmp_path): assert not safety(tmp_path).evaluate(reading(valid=False)).approved
def test_missing_soil_fails_closed(tmp_path): assert not safety(tmp_path).evaluate(reading(soil_moisture=None)).approved
def test_empty_tank_blocks(tmp_path): assert not safety(tmp_path).evaluate(reading(water_level=0)).approved
def test_manual_needs_valid_sensor_and_is_runtime_limited(tmp_path):
    result = safety(tmp_path).evaluate(reading(soil_moisture=55), "manual", 999)
    assert result.approved and result.duration_seconds == 60
def test_emergency_stop_blocks(tmp_path):
    engine = safety(tmp_path); engine.emergency = True
    assert not engine.evaluate(reading()).approved
