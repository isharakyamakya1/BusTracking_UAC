#define TINY_GSM_MODEM_SIM800

#include <TinyGsmClient.h>
#include <HTTPClient.h>
#include <TinyGPSPlus.h>

// -------------------------------------------------
// ESP32 + GPS + GSM (SIM800L) pour le prototype
// -------------------------------------------------
// Libraries required:
// - TinyGSM
// - TinyGPSPlus

// -----------------------------
// Configuration a personnaliser
// -----------------------------
const char* GSM_APN = "internet";
const char* GSM_USER = "";
const char* GSM_PASS = "";

// Exemple: "http://192.168.1.10:5000/api/update-location"
const char* SERVER_URL = "http://YOUR_SERVER_IP:5000/api/update-location";

// Utilise soit le bus_id, soit la plaque.
const bool USE_BUS_ID = false;
const int BUS_ID = 1;
const char* BUS_PLAQUE = "UAC-001";
const char* LAST_STOP = "En route";

// GPS sur Serial2
static const int GPS_RX_PIN = 16; // ESP32 RX2 <- TX GPS
static const int GPS_TX_PIN = 17; // ESP32 TX2 -> RX GPS
static const uint32_t GPS_BAUD = 9600;

// GSM sur Serial1
static const int GSM_RX_PIN = 27; // ESP32 RX1 <- TX SIM800L
static const int GSM_TX_PIN = 26; // ESP32 TX1 -> RX SIM800L
static const uint32_t GSM_BAUD = 9600;

// Intervalles
static const unsigned long GPS_SEND_INTERVAL_MS = 15000;
static const unsigned long GSM_RETRY_INTERVAL_MS = 15000;
static const unsigned long GPS_FIX_TIMEOUT_MS = 12000;

TinyGPSPlus gps;
HardwareSerial GpsSerial(2);
HardwareSerial GsmSerial(1);
TinyGsm modem(GsmSerial);
TinyGsmClient gsmClient(modem);

unsigned long lastSendMs = 0;
unsigned long lastGsmRetryMs = 0;

String escapeJson(const String& value) {
  String output;
  output.reserve(value.length() + 8);

  for (size_t i = 0; i < value.length(); i++) {
    const char c = value[i];
    switch (c) {
      case '\\':
        output += "\\\\";
        break;
      case '"':
        output += "\\\"";
        break;
      case '\n':
        output += "\\n";
        break;
      case '\r':
        break;
      case '\t':
        output += "\\t";
        break;
      default:
        output += c;
        break;
    }
  }

  return output;
}

bool connectGsm() {
  Serial.println("Initialisation du modem GSM...");

  modem.restart();
  if (!modem.waitForNetwork(60000L)) {
    Serial.println("Reseau GSM indisponible.");
    return false;
  }

  if (!modem.isNetworkConnected()) {
    Serial.println("Pas de connexion reseau GSM.");
    return false;
  }

  Serial.print("Operateur: ");
  Serial.println(modem.getOperator());

  if (!modem.gprsConnect(GSM_APN, GSM_USER, GSM_PASS)) {
    Serial.println("Connexion GPRS echouee.");
    return false;
  }

  if (!modem.isGprsConnected()) {
    Serial.println("GPRS non connecte.");
    return false;
  }

  Serial.println("GSM/GPRS connecte.");
  return true;
}

void readGpsData() {
  while (GpsSerial.available() > 0) {
    gps.encode(GpsSerial.read());
  }
}

bool hasValidLocation() {
  return gps.location.isValid() && gps.location.age() < GPS_FIX_TIMEOUT_MS;
}

String buildPayload(double latitude, double longitude) {
  String payload = "{";
  if (USE_BUS_ID) {
    payload += "\"bus_id\":";
    payload += String(BUS_ID);
    payload += ",";
  } else {
    payload += "\"plaque\":\"";
    payload += escapeJson(String(BUS_PLAQUE));
    payload += "\",";
  }
  payload += "\"latitude\":";
  payload += String(latitude, 6);
  payload += ",";
  payload += "\"longitude\":";
  payload += String(longitude, 6);
  payload += ",";
  payload += "\"dernier_arret\":\"";
  payload += escapeJson(String(LAST_STOP));
  payload += "\"";
  payload += "}";
  return payload;
}

bool postLocation(double latitude, double longitude) {
  if (!modem.isGprsConnected()) {
    if (!connectGsm()) {
      return false;
    }
  }

  HTTPClient http;
  if (!http.begin(gsmClient, SERVER_URL)) {
    Serial.println("Impossible d'initialiser HTTP.");
    return false;
  }

  http.addHeader("Content-Type", "application/json");

  const String payload = buildPayload(latitude, longitude);
  Serial.println("Envoi de la position via GSM...");
  Serial.println(payload);

  const int httpCode = http.POST(payload);
  const String response = http.getString();
  http.end();

  if (httpCode > 0) {
    Serial.print("HTTP code: ");
    Serial.println(httpCode);
    Serial.print("Reponse serveur: ");
    Serial.println(response);
    return httpCode >= 200 && httpCode < 300;
  }

  Serial.print("Erreur HTTP: ");
  Serial.println(httpCode);
  return false;
}

void printGpsDebug() {
  if (gps.location.isUpdated()) {
    Serial.print("GPS: ");
    Serial.print(gps.location.lat(), 6);
    Serial.print(", ");
    Serial.print(gps.location.lng(), 6);
    Serial.print(" | sats: ");
    Serial.print(gps.satellites.isValid() ? gps.satellites.value() : 0);
    Serial.print(" | hdop: ");
    Serial.println(gps.hdop.isValid() ? gps.hdop.hdop() : 0.0);
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println();
  Serial.println("Demarrage ESP32 Bus Tracker GSM");

  GpsSerial.begin(GPS_BAUD, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);
  GsmSerial.begin(GSM_BAUD, SERIAL_8N1, GSM_RX_PIN, GSM_TX_PIN);

  connectGsm();
}

void loop() {
  readGpsData();
  printGpsDebug();

  if (!modem.isGprsConnected() && millis() - lastGsmRetryMs >= GSM_RETRY_INTERVAL_MS) {
    lastGsmRetryMs = millis();
    connectGsm();
  }

  if (millis() - lastSendMs >= GPS_SEND_INTERVAL_MS) {
    lastSendMs = millis();

    if (hasValidLocation()) {
      const double latitude = gps.location.lat();
      const double longitude = gps.location.lng();
      const bool ok = postLocation(latitude, longitude);

      if (ok) {
        Serial.println("Position envoyee avec succes.");
      } else {
        Serial.println("Echec de l'envoi de la position.");
      }
    } else {
      Serial.println("Attente d'un fix GPS valide...");
    }
  }

  delay(20);
}
