#define TINY_GSM_MODEM_SIM800

#include <WiFi.h>
#include <HTTPClient.h>
#include <TinyGsmClient.h>
#include <TinyGPSPlus.h>

const char* WIFI_SSID = "ish";
const char* WIFI_PASS = "12345678@";
// Définissez ceci sur l'IP (ou le nom d'hôte) de la machine qui exécute l'application Flask.
// Exemple : "http://192.168.105.23:5000/api/update-location"
const char* WIFI_SERVER_URL = "http://192.168.110.87:5000/api/update-location";

const char* GSM_APN = "internet";
const char* GSM_USER = "";
const char* GSM_PASS = "";
const char* GSM_HOST = "";
const int GSM_PORT = 80;
const char* GSM_PATH = "/api/update-location";

const bool USE_BUS_ID = false;
const int BUS_ID = 1;
const char* BUS_PLAQUE = "UAC-001";
const char* API_KEY = "";
const char* DEFAULT_LAST_STOP = "En route";

static const int GPS_RX_PIN = 16;
static const int GPS_TX_PIN = 17;
static const uint32_t GPS_BAUD = 9600;

static const int GSM_RX_PIN = 27;
static const int GSM_TX_PIN = 26;
static const uint32_t GSM_BAUD = 9600;

static const unsigned long GPS_SEND_INTERVAL_MS = 15000;
static const unsigned long GPS_FIX_TIMEOUT_MS = 12000;
static const unsigned long WIFI_RETRY_INTERVAL_MS = 30000;
static const unsigned long GSM_RETRY_INTERVAL_MS = 30000;

TinyGPSPlus gps;
HardwareSerial gpsSerial(2);
HardwareSerial gsmSerial(1);
TinyGsm modem(gsmSerial);
TinyGsmClient gsmClient(modem);

unsigned long lastSendMs = 0;
unsigned long lastWifiRetryMs = 0;
unsigned long lastGsmRetryMs = 0;

String currentLastStop = DEFAULT_LAST_STOP;

String escapeJson(const String& value) {
  String output;
  output.reserve(value.length() + 8);
  for (size_t index = 0; index < value.length(); index++) {
    const char character = value[index];
    switch (character) {
      case '\\': output += "\\\\"; break;
      case '"': output += "\\\""; break;
      case '\n': output += "\\n"; break;
      case '\r': break;
      case '\t': output += "\\t"; break;
      default: output += character; break;
    }
  }
  return output;
}

void readGpsData() {
  while (gpsSerial.available() > 0) {
    gps.encode(gpsSerial.read());
  }
}

bool hasValidLocation() {
  return gps.location.isValid() && gps.location.age() < GPS_FIX_TIMEOUT_MS;
}

bool ensureWifiConnected() {
  if (WiFi.status() == WL_CONNECTED) {
    return true;
  }

  if (millis() - lastWifiRetryMs < WIFI_RETRY_INTERVAL_MS) {
    return false;
  }

  lastWifiRetryMs = millis();
  Serial.println("[WIFI] Reconnexion en cours...");
  WiFi.disconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 10000) {
    delay(250);
    Serial.print('.');
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("[WIFI] Connecté. IP : ");
    Serial.println(WiFi.localIP());
    return true;
  }

  Serial.println("[WIFI] Échec de la connexion.");
  return false;
}

bool ensureGsmConnected() {
  if (GSM_HOST[0] == '\0') {
    return false;
  }

  if (modem.isGprsConnected()) {
    return true;
  }

  if (millis() - lastGsmRetryMs < GSM_RETRY_INTERVAL_MS) {
    return false;
  }

  lastGsmRetryMs = millis();
  Serial.println("[GSM] Connexion modem...");
  modem.restart();

  if (!modem.waitForNetwork(60000L)) {
    Serial.println("[GSM] Réseau indisponible.");
    return false;
  }

  if (!modem.gprsConnect(GSM_APN, GSM_USER, GSM_PASS)) {
    Serial.println("[GSM] GPRS connection failed.");
    return false;
  }

  Serial.println("[GSM] GPRS connecté.");
  return true;
}

String buildPayload(double latitude, double longitude) {
  // Build a payload that includes multiple key aliases so the server
  // accepts the data regardless of which field it expects.
  String payload = "{";
  bool hasField = false;

  if (USE_BUS_ID && BUS_ID > 0) {
    payload += "\"bus_id\":" + String(BUS_ID);
    hasField = true;
  } else if (BUS_PLAQUE && BUS_PLAQUE[0] != '\0') {
    payload += "\"plaque\":\"" + escapeJson(String(BUS_PLAQUE)) + "\"";
    hasField = true;
  }

  if (hasField) {
    payload += ",";
  }

  // include both verbose and short coordinate keys
  payload += "\"latitude\":" + String(latitude, 6) + ",";
  payload += "\"longitude\":" + String(longitude, 6) + ",";
  payload += "\"lat\":" + String(latitude, 6) + ",";
  payload += "\"lon\":" + String(longitude, 6) + ",";

  // include both French and English stop name keys
  payload += "\"dernier_arret\":\"" + escapeJson(currentLastStop) + "\",";
  payload += "\"last_stop\":\"" + escapeJson(currentLastStop) + "\"";

  payload += "}";
  return payload;
}

bool postLocationWiFi(const String& payload) {
  if (!ensureWifiConnected()) {
    return false;
  }

  HTTPClient http;
  http.setTimeout(10000);

  if (!http.begin(WIFI_SERVER_URL)) {
    Serial.println("[WIFI] HTTP begin failed.");
    return false;
  }

  http.addHeader("Content-Type", "application/json");
  if (API_KEY && API_KEY[0] != '\0') {
    http.addHeader("X-API-Key", API_KEY);
  }

  int httpCode = http.POST(payload);
  String response = httpCode > 0 ? http.getString() : "";
  http.end();

  Serial.print("[WIFI] HTTP code: ");
  Serial.println(httpCode);
  if (response.length() > 0) {
    Serial.print("[WIFI] Réponse: ");
    Serial.println(response);
  }

  return httpCode >= 200 && httpCode < 300;
}

bool postLocationGsm(const String& payload) {
  if (!ensureGsmConnected()) {
    return false;
  }

  if (!gsmClient.connect(GSM_HOST, GSM_PORT)) {
    Serial.println("[GSM] TCP connection failed.");
    return false;
  }

  String request = String("POST ") + GSM_PATH + " HTTP/1.1\r\n";
  request += String("Host: ") + GSM_HOST + "\r\n";
  request += "Connection: close\r\n";
  request += "Content-Type: application/json\r\n";
  request += String("Content-Length: ") + String(payload.length()) + "\r\n";
  if (API_KEY && API_KEY[0] != '\0') {
    request += String("X-API-Key: ") + API_KEY + "\r\n";
  }
  request += "\r\n";
  request += payload;

  gsmClient.print(request);

  unsigned long start = millis();
  while (!gsmClient.available() && gsmClient.connected() && millis() - start < 10000) {
    delay(10);
  }

  String statusLine = gsmClient.readStringUntil('\n');
  statusLine.trim();

  int httpCode = 0;
  int firstSpace = statusLine.indexOf(' ');
  if (firstSpace >= 0) {
    int secondSpace = statusLine.indexOf(' ', firstSpace + 1);
    String codeText = secondSpace >= 0
      ? statusLine.substring(firstSpace + 1, secondSpace)
      : statusLine.substring(firstSpace + 1);
    httpCode = codeText.toInt();
  }

  while (gsmClient.available()) {
    String line = gsmClient.readStringUntil('\n');
    line.trim();
    if (line.length() == 0) {
      break;
    }
  }

  String responseBody;
  while (gsmClient.available()) {
    responseBody += char(gsmClient.read());
  }

  gsmClient.stop();

  Serial.print("[GSM] HTTP code: ");
  Serial.println(httpCode);
  if (responseBody.length() > 0) {
    Serial.print("[GSM] Réponse: ");
    Serial.println(responseBody);
  }

  return httpCode >= 200 && httpCode < 300;
}

bool sendLocation(double latitude, double longitude) {
  String payload = buildPayload(latitude, longitude);

  Serial.print("[GPS] Sending payload: ");
  Serial.println(payload);

  if (postLocationWiFi(payload)) {
    Serial.println("[SYSTEM] Sent through WiFi.");
    return true;
  }

  if (postLocationGsm(payload)) {
    Serial.println("[SYSTEM] Sent through GSM fallback.");
    return true;
  }

  Serial.println("[SYSTEM] Send failed on both channels.");
  return false;
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println();
  Serial.println("Démarrage du traceur de bus UAC...");

  gpsSerial.begin(GPS_BAUD, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);
  gsmSerial.begin(GSM_BAUD, SERIAL_8N1, GSM_RX_PIN, GSM_TX_PIN);

  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.persistent(false);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  Serial.print("[WIFI] Connexion à : ");
  Serial.println(WIFI_SSID);

  if (GSM_HOST[0] != '\0') {
    Serial.println("[GSM] Fallback is enabled.");
  } else {
    Serial.println("[GSM] Fallback is disabled.");
  }
}

void loop() {
  readGpsData();

  if (millis() - lastSendMs < GPS_SEND_INTERVAL_MS) {
    delay(20);
    return;
  }

  lastSendMs = millis();

  if (!hasValidLocation()) {
    Serial.println("[GPS] Waiting for a valid fix...");
    delay(20);
    return;
  }

  sendLocation(gps.location.lat(), gps.location.lng());
  delay(20);
}