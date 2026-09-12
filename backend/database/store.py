from __future__ import annotations
import json, sqlite3
from pathlib import Path
from typing import Any

class Store:
    def __init__(self, url: str):
        self.path = Path(url.removeprefix("sqlite:///")); self.initialize()
    def connection(self):
        con = sqlite3.connect(self.path); con.row_factory = sqlite3.Row; return con
    def initialize(self):
        with self.connection() as con:
            con.executescript("""
            CREATE TABLE IF NOT EXISTS sensor_readings (id INTEGER PRIMARY KEY, timestamp TEXT NOT NULL, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS irrigation_events (id INTEGER PRIMARY KEY, timestamp TEXT NOT NULL, event TEXT NOT NULL, reason TEXT, duration INTEGER, mode TEXT, result TEXT);
            CREATE TABLE IF NOT EXISTS alerts (id INTEGER PRIMARY KEY, timestamp TEXT NOT NULL, key TEXT UNIQUE, severity TEXT, message TEXT);
            CREATE TABLE IF NOT EXISTS ai_predictions (id INTEGER PRIMARY KEY, timestamp TEXT NOT NULL, prediction TEXT, confidence REAL, explanation TEXT);
            """)
    def add_reading(self, reading: dict[str, Any]):
        with self.connection() as con: con.execute("INSERT INTO sensor_readings(timestamp,payload) VALUES (?,?)", (reading["timestamp"], json.dumps(reading)))
    def latest(self) -> dict[str, Any] | None:
        with self.connection() as con: row = con.execute("SELECT payload FROM sensor_readings ORDER BY id DESC LIMIT 1").fetchone()
        return json.loads(row["payload"]) if row else None
    def history(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.connection() as con: rows = con.execute("SELECT payload FROM sensor_readings ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return list(reversed([json.loads(r["payload"]) for r in rows]))
    def log_irrigation(self, timestamp: str, event: str, reason: str, duration: int, mode: str, result: str):
        with self.connection() as con: con.execute("INSERT INTO irrigation_events VALUES (NULL,?,?,?,?,?,?)", (timestamp,event,reason,duration,mode,result))
    def last_irrigation(self) -> dict[str, Any] | None:
        with self.connection() as con: r = con.execute("SELECT * FROM irrigation_events WHERE event='IRRIGATION_STARTED' ORDER BY id DESC LIMIT 1").fetchone()
        return dict(r) if r else None
    def add_alert_once(self, timestamp: str, key: str, severity: str, message: str) -> bool:
        try:
            with self.connection() as con: con.execute("INSERT INTO alerts VALUES(NULL,?,?,?,?)", (timestamp,key,severity,message))
            return True
        except sqlite3.IntegrityError: return False
    def alerts(self) -> list[dict[str, Any]]:
        with self.connection() as con: return [dict(r) for r in con.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT 30")]
