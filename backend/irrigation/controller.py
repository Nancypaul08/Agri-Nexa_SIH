from __future__ import annotations
from datetime import datetime, timezone
from threading import Timer
from backend.config import Settings

class PumpController:
    """Actuator boundary: only safety-approved commands reach this class."""
    def __init__(self, settings: Settings): self.settings, self.running, self._stop_timer = settings, False, None
    def command(self, enabled: bool, duration: int = 0) -> dict:
        # In MOCK_MODE no hardware command is emitted. Firmware accepts PUMP_ON:<seconds>/PUMP_OFF.
        if not self.settings.mock_mode:
            try:
                import serial
                with serial.Serial(self.settings.device_port, self.settings.device_baud_rate, timeout=1) as port:
                    port.write((f"PUMP_ON:{duration}\n" if enabled else "PUMP_OFF\n").encode())
            except Exception as exc:
                return {"ok": False, "message": f"Device command failed; pump state unchanged: {exc}"}
        self.running = enabled
        if enabled and self.settings.mock_mode:
            # Mirrors the firmware watchdog in a safe demo; real hardware has its own cutoff.
            if self._stop_timer: self._stop_timer.cancel()
            self._stop_timer = Timer(duration, lambda: self.command(False))
            self._stop_timer.daemon = True
            self._stop_timer.start()
        elif not enabled and self._stop_timer:
            self._stop_timer.cancel(); self._stop_timer = None
        return {"ok": True, "pump_status": enabled, "timestamp": datetime.now(timezone.utc).isoformat(), "mode": "mock" if self.settings.mock_mode else "serial"}
