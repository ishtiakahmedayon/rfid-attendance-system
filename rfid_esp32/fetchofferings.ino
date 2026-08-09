bool fetchOfferings()
{
    int code = -1;
    String payload = "";

    for (int attempt = 1; attempt <= HTTP_RETRIES; attempt++) {
        WiFiClientSecure client;
        client.setInsecure();

        HTTPClient http;
        http.setFollowRedirects(HTTPC_STRICT_FOLLOW_REDIRECTS);
        http.setTimeout(HTTP_TIMEOUT_MS);

        bool started = http.begin(client, String(SERVER)+"/offerings");
        if (!started) {
            Serial.printf("[GET /offerings] attempt %d/%d begin failed\n", attempt, HTTP_RETRIES);
            if (attempt < HTTP_RETRIES) delay(1000 * attempt);
            continue;
        }

        http.addHeader("X-API-Key", API_KEY);
        code = http.GET();
        payload = (code > 0) ? http.getString() : "";

        Serial.printf("[GET /offerings] attempt %d/%d code=%d\n", attempt, HTTP_RETRIES, code);
        Serial.println(payload);

        http.end();

        if (code == 200) break;
        if (attempt < HTTP_RETRIES) delay(1000 * attempt);
    }

    if (code != 200) {
        display.clearDisplay();
        display.println("Offerings Error");
        display.print("Code: ");
        display.println(code);
        display.display();
        delay(1200);
        return false;
    }

    DynamicJsonDocument doc(2048);   // bump this up if you add many offerings
    DeserializationError err = deserializeJson(doc, payload);

    if (err) {
        Serial.print("[GET /offerings] JSON parse failed: ");
        Serial.println(err.c_str());
        return false;
    }

    offeringCount = 0;
    for (JsonObject offering : doc.as<JsonArray>()) {
        if (offeringCount >= MAX_OFFERINGS) break;

        offeringIds[offeringCount] = offering["offering_id"].as<long>();

        String label = offering["course_code"].as<String>();
        offeringLabels[offeringCount] = label;

        offeringCount++;
    }

    return offeringCount > 0;
}
