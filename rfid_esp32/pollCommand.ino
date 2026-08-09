// Polls the server to find out whether a session is currently Open.
// This is level-triggered: the server always reports the current state
// (not a one-shot "start now" event), so a missed poll just gets
// corrected on the next one a few seconds later instead of losing an
// instruction.
//
// Returns true if a session is currently active, and fills in the
// out-params with its session_id / offering_id / course_code.
// Returns false (and leaves the out-params untouched) if nothing is
// open, or if the request itself failed -- a failed poll should never
// be treated as "stop", since that could kill an in-progress session
// just because of a flaky WiFi moment. Callers should keep whatever
// state they already had when this returns false due to a request
// failure (see requestOk).
bool pollDeviceCommand(long &outSessionId, long &outOfferingId, String &outCourseCode, bool &requestOk)
{
    requestOk = false;

    WiFiClientSecure client;
    client.setInsecure();

    HTTPClient http;
    http.setFollowRedirects(HTTPC_STRICT_FOLLOW_REDIRECTS);
    http.setTimeout(HTTP_TIMEOUT_MS);

    bool started = http.begin(client, String(SERVER)+"/device_command");
    if (!started) {
        Serial.println("[GET /device_command] begin failed");
        return false;
    }

    http.addHeader("X-API-Key", API_KEY);
    int code = http.GET();
    String payload = (code > 0) ? http.getString() : "";
    http.end();

    if (code != 200) {
        Serial.printf("[GET /device_command] code=%d\n", code);
        return false;
    }

    DynamicJsonDocument doc(256);
    DeserializationError err = deserializeJson(doc, payload);
    if (err) {
        Serial.print("[GET /device_command] JSON parse failed: ");
        Serial.println(err.c_str());
        return false;
    }

    requestOk = true;

    bool active = doc["active"] | false;
    if (!active) {
        return false;
    }

    outSessionId = doc["session_id"] | -1;
    outOfferingId = doc["offering_id"] | -1;
    outCourseCode = doc["course_code"] | "";

    return outSessionId > 0;
}
