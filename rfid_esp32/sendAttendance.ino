void sendAttendance(String uid)
{
    if(currentSession==-1)
    {
        display.clearDisplay();
        display.println("No Session");
        display.display();
        delay(1000);
        return;
    }

    String json =
    "{\"session_id\":"
    +String(currentSession)+
    ",\"uid\":\""+
    uid+
    "\"}";

    int code = -1;
    String payload = "";

    for (int attempt = 1; attempt <= HTTP_RETRIES; attempt++) {
        WiFiClientSecure client;
        client.setInsecure();

        HTTPClient http;
        http.setFollowRedirects(HTTPC_STRICT_FOLLOW_REDIRECTS);
        http.setTimeout(HTTP_TIMEOUT_MS);

        bool started = http.begin(client, String(SERVER)+"/scan");
        if (!started) {
            Serial.printf("[POST /scan] attempt %d/%d begin failed\n", attempt, HTTP_RETRIES);
            if (attempt < HTTP_RETRIES) delay(1000 * attempt);
            continue;
        }

        http.addHeader("Content-Type","application/json");
        http.addHeader("X-API-Key", API_KEY);
        code = http.POST(json);
        payload = (code > 0) ? http.getString() : "";

        Serial.printf("[POST /scan] attempt %d/%d code=%d\n", attempt, HTTP_RETRIES, code);
        Serial.println(payload);

        http.end();

        if (code == 200) break;
        if (attempt < HTTP_RETRIES) delay(1000 * attempt);
    }

    if(code==200)
    {
        DynamicJsonDocument doc(512);

        DeserializationError err = deserializeJson(doc, payload);

        if (err) {
            Serial.print("JSON parse failed: ");
            Serial.println(err.c_str());

            display.clearDisplay();
            display.println("Bad JSON");
            display.display();
            delay(1000);
            return;
        }

        display.clearDisplay();

        bool success = doc["success"] | false;

        if (success) {
            const char* student = doc["student"] | "Unknown";
            const char* status  = doc["status"]  | "Unknown";
            beep(1,100);
            digitalWrite(LED_PIN, HIGH);
            delay(100);
            digitalWrite(LED_PIN, LOW);

            display.println(student);
            display.println(status);
        } else {
            // Unknown Card / Not Enrolled / Already Present / Invalid Session
            const char* message = doc["message"] | "Rejected";
            beep(1,100);
            digitalWrite(LED_RED, HIGH);
            delay(100);
            digitalWrite(LED_RED, LOW);
            display.println("Rejected:");
            display.println(message);
        }

        display.display();




        delay(500);
    }
    else
    {
        display.clearDisplay();
        display.println("Scan API Error");
        display.print("Code: ");
        display.println(code);
        display.display();

        delay(1200);
    }
}