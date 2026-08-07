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

    HTTPClient http;

    http.begin(String(SERVER)+"/scan");

    http.addHeader("Content-Type","application/json");

    String json =
    "{\"session_id\":"
    +String(currentSession)+
    ",\"uid\":\""+
    uid+
    "\"}";

    int code = http.POST(json);
    Serial.print("HTTP Code: ");
    Serial.println(code);

    String payload = http.getString();   // read the body ONCE, reuse it below
    Serial.println(payload);

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

            http.end();
            return;
        }

        display.clearDisplay();

        bool success = doc["success"] | false;

        if (success) {
            const char* student = doc["student"] | "Unknown";
            const char* status  = doc["status"]  | "Unknown";

            display.println(student);
            display.println(status);
        } else {
            // Unknown Card / Not Enrolled / Already Present / Invalid Session
            const char* message = doc["message"] | "Rejected";

            display.println("Rejected:");
            display.println(message);
        }

        display.display();

        beep(1,100);
        digitalWrite(LED_PIN, HIGH);
        delay(50);
        digitalWrite(LED_PIN, LOW);


        delay(500);
    }
    else
    {
        display.clearDisplay();

        display.println("API Error");

        display.display();

        delay(1000);
    }

    http.end();
}