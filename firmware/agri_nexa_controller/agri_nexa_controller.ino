/* AGRI NEXA — Arduino UNO R4 firmware.
   Soil A0 | TDS A1 | DHT11 D2 | relay D7. Pump power goes through relay contacts only.
   Serial telemetry is JSON. Commands: MODE:REMOTE, MODE:AUTO, PUMP_ON:30, PUMP_OFF. */
#include <DHT.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

#define SOIL_PIN A0
#define TDS_PIN A1
#define DHT_PIN 2
#define DHT_TYPE DHT11
#define RELAY_PIN 7
#define RELAY_ACTIVE_LOW true

LiquidCrystal_I2C lcd(0x27, 16, 2);
DHT dht(DHT_PIN, DHT_TYPE);
const int SOIL_DRY_LIMIT = 30, SOIL_WET_LIMIT = 60;
const unsigned long MAX_PUMP_RUNTIME_MS = 60000UL, PUMP_COOLDOWN_MS = 300000UL;
const unsigned long REPORT_INTERVAL_MS = 5000UL, SCREEN_INTERVAL_MS = 2000UL;
bool pumpState = false, remoteMode = false;
unsigned long pumpStartedAt = 0, pumpStoppedAt = 0, lastReportAt = 0, lastScreenAt = 0;
byte screen = 0;

void relayWrite(bool on) { digitalWrite(RELAY_PIN, (on ^ RELAY_ACTIVE_LOW) ? HIGH : LOW); }
bool canStartPump() { return !pumpState && (pumpStoppedAt == 0 || millis() - pumpStoppedAt >= PUMP_COOLDOWN_MS); }
void setPump(bool on) {
  if (on && !canStartPump()) return;
  pumpState = on; relayWrite(on);
  if (on) pumpStartedAt = millis(); else pumpStoppedAt = millis();
}
int soilPercent() { return constrain(map(analogRead(SOIL_PIN), 4095, 0, 0, 100), 0, 100); }
float tdsPpm() {
  float voltage = analogRead(TDS_PIN) * 5.0f / 4095.0f;
  return (133.42f * voltage * voltage * voltage - 255.86f * voltage * voltage + 857.39f * voltage) * 0.5f;
}
void printNumberOrNull(float value, byte decimals) { if (isnan(value)) Serial.print("null"); else Serial.print(value, decimals); }
void reportReading(int soil, float tds, float temperature, float humidity) {
  Serial.print("{\"soil_moisture\":"); Serial.print(soil);
  Serial.print(",\"tds\":"); Serial.print(tds, 0);
  Serial.print(",\"temperature\":"); printNumberOrNull(temperature, 1);
  Serial.print(",\"humidity\":"); printNumberOrNull(humidity, 1);
  Serial.print(",\"pump_status\":"); Serial.print(pumpState ? "true" : "false"); Serial.println("}");
}
void updateLcd(int soil, float tds, float temperature, float humidity) {
  lcd.clear();
  if (screen == 0) {
    lcd.setCursor(0, 0); lcd.print("Soil: "); lcd.print(soil); lcd.print("%");
    lcd.setCursor(0, 1); lcd.print("Pump: "); lcd.print(pumpState ? "ON" : "OFF");
  } else if (screen == 1) {
    lcd.setCursor(0, 0); lcd.print("Temp: "); if (isnan(temperature)) lcd.print("ERROR"); else { lcd.print(temperature, 1); lcd.print("C"); }
    lcd.setCursor(0, 1); lcd.print("Hum: "); if (isnan(humidity)) lcd.print("ERROR"); else { lcd.print(humidity, 1); lcd.print("%"); }
  } else {
    lcd.setCursor(0, 0); lcd.print("TDS:"); lcd.print(tds, 0); lcd.print(" ppm");
    lcd.setCursor(0, 1); lcd.print(remoteMode ? "Mode: REMOTE" : "Mode: AUTO");
  }
  screen = (screen + 1) % 3;
}
void handleCommand() {
  String command = Serial.readStringUntil('\n'); command.trim();
  if (command == "MODE:REMOTE") remoteMode = true;
  else if (command == "MODE:AUTO") remoteMode = false;
  else if (command == "PUMP_OFF") { remoteMode = true; setPump(false); }
  else if (command.startsWith("PUMP_ON:")) {
    long seconds = command.substring(8).toInt();
    if (seconds > 0 && seconds <= (MAX_PUMP_RUNTIME_MS / 1000UL)) { remoteMode = true; setPump(true); }
  }
}
void setup() {
  Serial.begin(9600); analogReadResolution(12);  // UNO R4-specific
  dht.begin(); pinMode(RELAY_PIN, OUTPUT); relayWrite(false);
  lcd.init(); lcd.backlight(); lcd.clear(); lcd.setCursor(0, 0); lcd.print("AGRI-NEXA"); lcd.setCursor(0, 1); lcd.print("Plant Monitor"); delay(1500);
}
void loop() {
  if (Serial.available()) handleCommand();
  int soil = soilPercent(); float temperature = dht.readTemperature(), humidity = dht.readHumidity(), tds = tdsPpm();
  // Independent deterministic hardware safety: operates even if backend/internet is unavailable.
  if (pumpState && millis() - pumpStartedAt >= MAX_PUMP_RUNTIME_MS) setPump(false);
  if (!remoteMode && !pumpState && soil < SOIL_DRY_LIMIT && canStartPump()) setPump(true);
  if (!remoteMode && pumpState && soil > SOIL_WET_LIMIT) setPump(false);
  if (millis() - lastReportAt >= REPORT_INTERVAL_MS) { lastReportAt = millis(); reportReading(soil, tds, temperature, humidity); }
  if (millis() - lastScreenAt >= SCREEN_INTERVAL_MS) { lastScreenAt = millis(); updateLcd(soil, tds, temperature, humidity); }
}
