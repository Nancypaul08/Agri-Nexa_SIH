from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}

@dataclass(frozen=True)
class Settings:
    soil_moisture_threshold: float = float(os.getenv("SOIL_MOISTURE_THRESHOLD", "30"))
    soil_moisture_sufficient: float = float(os.getenv("SOIL_MOISTURE_SUFFICIENT", "60"))
    max_pump_runtime: int = int(os.getenv("MAX_PUMP_RUNTIME", "60"))
    pump_cooldown: int = int(os.getenv("PUMP_COOLDOWN", "300"))
    temperature_limit: float = float(os.getenv("TEMPERATURE_LIMIT", "40"))
    humidity_limit: float = float(os.getenv("HUMIDITY_LIMIT", "90"))
    device_port: str = os.getenv("DEVICE_PORT", "/dev/ttyUSB0")
    device_baud_rate: int = int(os.getenv("DEVICE_BAUD_RATE", "9600"))
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./agri_nexa.db")
    mock_mode: bool = _bool("MOCK_MODE", True)
    relay_active_low: bool = _bool("RELAY_ACTIVE_LOW", True)

settings = Settings()
