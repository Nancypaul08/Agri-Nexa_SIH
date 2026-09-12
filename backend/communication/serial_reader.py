"""Bridge newline-delimited JSON emitted by firmware to the local API."""
import json, urllib.request
from backend.config import settings

def main():
    if settings.mock_mode: raise SystemExit("MOCK_MODE=true: serial reader intentionally disabled.")
    import serial
    with serial.Serial(settings.device_port, settings.device_baud_rate, timeout=2) as port:
        print(f"Listening on {settings.device_port}")
        while True:
            try:
                payload = json.loads(port.readline().decode().strip())
                req = urllib.request.Request("http://127.0.0.1:8000/api/sensors/ingest", data=json.dumps(payload).encode(), headers={"Content-Type":"application/json"}, method="POST")
                urllib.request.urlopen(req, timeout=3).read()
            except (json.JSONDecodeError, UnicodeDecodeError): pass
            except Exception as exc: print(f"serial bridge: {exc}")
if __name__ == "__main__": main()
