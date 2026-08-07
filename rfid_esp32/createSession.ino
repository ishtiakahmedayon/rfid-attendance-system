void createSession(long offeringId, String offeringLabel)
{
    currentCourse = offeringLabel;   // used only for the OLED "Session Started" screen
    currentSession = -1;

    HTTPClient http;
    http.begin(String(SERVER)+"/start_session");
    http.addHeader("Content-Type","application/json");

    String json = "{\"offering_id\":"+String(offeringId)+"}";

    int code = http.POST(json);

    if (code==200)
    {
        String payload = http.getString();
        Serial.println(payload);

        DynamicJsonDocument doc(256);
        deserializeJson(doc, payload);

        currentSession = doc["session_id"];

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
        display.println("API ERROR");
        display.display();
        delay(1000);
    }

    http.end();
}
