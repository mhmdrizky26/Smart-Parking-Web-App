#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>

const char* ssid = "Y";              // ganti sesuai WiFi
const char* password = "1234567890"; // ganti sesuai WiFi

WebServer server(80);

// Daftar pin LED (10 buah)
int ledPins[10] = {2, 4, 5, 18, 19, 21, 22, 23, 25, 26};

void handleUpdate() {
  if (server.hasArg("plain")) {
    String body = server.arg("plain");
    Serial.println("Data diterima: " + body);

    DynamicJsonDocument doc(2048);  // buffer lebih besar
    DeserializationError error = deserializeJson(doc, body);

    if (error) {
      server.send(400, "application/json", "{\"error\":\"json parse failed\"}");
      return;
    }

    // Pastikan jumlah slot sesuai dengan LED
    int i = 0;
    for (JsonObject slot : doc.as<JsonArray>()) {
      if (i < 10) { // hanya ambil 10 slot pertama
        bool occupied = slot["occupied"];
        digitalWrite(ledPins[i], occupied ? HIGH : LOW);
        Serial.printf("Slot %d -> %s\n", i, occupied ? "OCCUPIED" : "EMPTY");
      }
      i++;
    }

    server.send(200, "application/json", "{\"status\":\"ok\"}");
  } else {
    server.send(400, "application/json", "{\"error\":\"no data\"}");
  }
}

void setup() {
  Serial.begin(115200);

  // Set pin LED sebagai output
  for (int i = 0; i < 10; i++) {
    pinMode(ledPins[i], OUTPUT);
    digitalWrite(ledPins[i], LOW); // awalnya mati
  }

  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi..");
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }
  Serial.println("\nConnected!");
  Serial.println(WiFi.localIP());

  server.on("/update", HTTP_POST, handleUpdate);
  server.begin();
}

void loop() {
  server.handleClient();
}
