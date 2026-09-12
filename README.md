# AGRI NEXA

Offline-first AI + IoT smart farming assistant. The first implementation closes the reliable path:

`sensor -> validation -> safety decision -> relay command -> pump -> SQLite log -> dashboard`

The agent explains decisions but never controls a GPIO or bypasses the irrigation safety layer.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn backend.api.main:app --reload --port 8000
```

Open http://localhost:8000. Start in `MOCK_MODE=true` unless the device is connected. To use serial hardware, set `MOCK_MODE=false` and `DEVICE_PORT` in `.env`; then start the serial reader:

```bash
python -m backend.communication.serial_reader
```

Run tests with `pytest`.

## Hardware safety

The UNO R4 firmware retains the supplied mapping: soil sensor `A0`, TDS sensor `A1`, DHT11 `D2`, and relay `D7`; it also supports a 16×2 I²C LCD at `0x27`. Install the Arduino `DHT sensor library` and `LiquidCrystal I2C` library, then upload [agri_nexa_controller.ino](firmware/agri_nexa_controller/agri_nexa_controller.ino). The pump is powered through relay contacts only—never GPIO. Configure relay active level via `RELAY_ACTIVE_LOW`. The backend and firmware both have a maximum runtime/cooldown; the backend additionally fails closed for invalid/missing soil data or an explicitly empty water tank.

At boot, the controller provides deterministic local moisture control so irrigation remains available offline. The first backend `PUMP_ON`/`PUMP_OFF` command changes it to `REMOTE` mode, where the backend safety engine controls the relay. Send `MODE:AUTO` over serial only when you intentionally want to return to local automatic mode.

## API

- `POST /api/sensors/ingest` receives device JSON.
- `GET /api/farm/status` returns fused state and deterministic irrigation decision.
- `POST /api/irrigation/manual` requests a manually controlled cycle (still safety checked).
- `POST /api/irrigation/automatic` evaluates/starts automatic irrigation.
- `POST /api/irrigation/emergency-stop` stops the pump immediately.
- `POST /api/agent/chat` gets a farmer-friendly grounded answer.

Optional sensors (NPK, pH, EC/TDS, water level, image analysis) are accepted when present and safely omitted when unavailable.
