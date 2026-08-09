// Tells the server to close the given session. Used when the device
// itself ends the session (teacher presses NEXT/Back at the device
// instead of using the dashboard "End Session" button).
void sendEndSession(long sessionId)
{
    if (sessionId <= 0) {
        return;
    }

    String json = "{\"session_id\":"+String(sessionId)+"}";
    int code = -1;
    String payload = "";

    for (int attempt = 1; attempt <= HTTP_RETRIES; attempt++) {
        WiFiClientSecure client;
        client.setInsecure();

        HTTPClient http;
        http.setFollowRedirects(HTTPC_STRICT_FOLLOW_REDIRECTS);
        http.setTimeout(HTTP_TIMEOUT_MS);

        bool started = http.begin(client, String(SERVER)+"/end_session");
        if (!started) {
            Serial.printf("[POST /end_session] attempt %d/%d begin failed\n", attempt, HTTP_RETRIES);
            if (attempt < HTTP_RETRIES) delay(1000 * attempt);
            continue;
        }

        http.addHeader("Content-Type","application/json");
        http.addHeader("X-API-Key", API_KEY);
        code = http.POST(json);
        payload = (code > 0) ? http.getString() : "";

        Serial.printf("[POST /end_session] attempt %d/%d code=%d\n", attempt, HTTP_RETRIES, code);
        Serial.println(payload);

        http.end();

        if (code == 200) break;
        if (attempt < HTTP_RETRIES) delay(1000 * attempt);
    }

    display.clearDisplay();
    display.setCursor(0,0);
    if (code == 200) {
        display.println("Session Ended");
    } else {
        display.println("End Session Err");
        display.print("Code: ");
        display.println(code);
    }
    display.display();
    beep(1,150);
    delay(900);
}
