void createSession(long offeringId, String offeringLabel)
{
    currentCourse = offeringLabel;   // used only for the OLED "Session Started" screen
    currentSession = -1;

    String json = "{\"offering_id\":"+String(offeringId)+"}";
    int code = -1;
    String payload = "";

    for (int attempt = 1; attempt <= HTTP_RETRIES; attempt++) {
        WiFiClientSecure client;
        client.setInsecure();

        HTTPClient http;
        http.setFollowRedirects(HTTPC_STRICT_FOLLOW_REDIRECTS);
        http.setTimeout(HTTP_TIMEOUT_MS);

        bool started = http.begin(client, String(SERVER)+"/start_session");
        if (!started) {
            Serial.printf("[POST /start_session] attempt %d/%d begin failed\n", attempt, HTTP_RETRIES);
            if (attempt < HTTP_RETRIES) delay(1000 * attempt);
            continue;
        }

        http.addHeader("Content-Type","application/json");
        code = http.POST(json);
        payload = (code > 0) ? http.getString() : "";

        Serial.printf("[POST /start_session] attempt %d/%d code=%d\n", attempt, HTTP_RETRIES, code);
        Serial.println(payload);

        http.end();

        if (code == 200) break;
        if (attempt < HTTP_RETRIES) delay(1000 * attempt);
    }

    if (code==200)
    {
        DynamicJsonDocument doc(256);
        DeserializationError err = deserializeJson(doc, payload);
        if (err) {
            Serial.print("[POST /start_session] JSON parse failed: ");
            Serial.println(err.c_str());
            display.clearDisplay();
            display.println("Session JSON Err");
            display.display();
            delay(1200);
            return;
        }

        currentSession = doc["session_id"];
        if (currentSession <= 0) {
            display.clearDisplay();
            display.println("Session ID Bad");
            display.display();
            delay(1200);
            return;
        }

        display.clearDisplay();
        display.println("Session Started");
        display.println(currentCourse);
        display.print("ID:");
        display.println(currentSession);
        display.display();

        beep(1,100);
        delay(1000);
    }
    else
    {
        display.clearDisplay();
        display.println("Session API Err");
        display.print("Code: ");
        display.println(code);
        display.display();
        delay(1200);
    }
}
