bool fetchOfferings()
{
    HTTPClient http;
    http.begin(String(SERVER)+"/offerings");

    int code = http.GET();

    if (code != 200) {
        http.end();
        return false;
    }

    String payload = http.getString();
    http.end();

    DynamicJsonDocument doc(2048);   // bump this up if you add many offerings
    DeserializationError err = deserializeJson(doc, payload);

    if (err) {
        return false;
    }

    offeringCount = 0;
    for (JsonObject offering : doc.as<JsonArray>()) {
        if (offeringCount >= MAX_OFFERINGS) break;

        offeringIds[offeringCount] = offering["offering_id"].as<long>();

        String label = offering["course_code"].as<String>()
                     + " (" + offering["batch"].as<String>() + ")";
        offeringLabels[offeringCount] = label;

        offeringCount++;
    }

    return offeringCount > 0;
}
