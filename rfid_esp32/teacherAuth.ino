// Reads a card UID within a timeout window, without touching session
// state or sending attendance -- used only for the teacher card-tap
// confirmation step below. Kept separate from readCard() (readcard.ino)
// deliberately: that function is tightly coupled to attendance-sending
// and session state, which has nothing to do with this one-off identity
// check before a session even exists yet.
// Returns the UID string (same hex format used elsewhere), or "" if the
// timeout elapsed or NEXT was pressed to cancel.
String readCardUidWithTimeout(unsigned long timeoutMs) {
  uint8_t uid[7];
  uint8_t uidLength;

  unsigned long start = millis();

  while (millis() - start < timeoutMs) {
    if (buttonPressed(BTN_NEXT)) {
      return "";   // manual cancel
    }

    bool success = nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, uid, &uidLength, 50);
    if (success) {
      String uidString = "";
      for (int i = 0; i < uidLength; i++) {
        if (uid[i] < 0x10) uidString += "0";
        uidString += String(uid[i], HEX);
      }
      uidString.toUpperCase();
      return uidString;
    }
  }

  return "";   // timed out
}

// Calls /verify_teacher_card. Only an explicit server match=true counts
// as confirmed -- any failure (bad response, no connection, timeout) is
// treated as "not confirmed", never as an automatic pass, since this is
// a security gate, not a convenience feature.
bool verifyTeacherCard(String uid, long offeringId) {
  String json = "{\"uid\":\""+uid+"\",\"offering_id\":"+String(offeringId)+"}";

  WiFiClientSecure client;
  client.setInsecure();

  HTTPClient http;
  http.setFollowRedirects(HTTPC_STRICT_FOLLOW_REDIRECTS);
  http.setTimeout(HTTP_TIMEOUT_MS);

  bool started = http.begin(client, String(SERVER)+"/verify_teacher_card");
  if (!started) {
    Serial.println("[POST /verify_teacher_card] begin failed");
    return false;
  }

  http.addHeader("Content-Type","application/json");
  http.addHeader("X-API-Key", API_KEY);
  int code = http.POST(json);
  String payload = (code > 0) ? http.getString() : "";
  http.end();

  Serial.printf("[POST /verify_teacher_card] code=%d\n", code);
  Serial.println(payload);

  if (code != 200) {
    return false;
  }

  DynamicJsonDocument doc(256);
  DeserializationError err = deserializeJson(doc, payload);
  if (err) {
    Serial.print("[POST /verify_teacher_card] JSON parse failed: ");
    Serial.println(err.c_str());
    return false;
  }

  bool success = doc["success"] | false;
  bool match = doc["match"] | false;

  return success && match;
}

// Shows the "tap teacher card" screen, reads a card within the timeout,
// and verifies it against the server. Returns true only on a confirmed
// match against the offering's own assigned teacher -- any other
// outcome (timeout, mismatch, cancel, network failure) returns false
// and the caller must not start the session.
bool confirmTeacherCard(long offeringId) {
  const unsigned long CONFIRM_TIMEOUT_MS = 5000;   // 5s, per spec

  display.clearDisplay();
  display.setCursor(0,0);
  display.println("Tap teacher card");
  display.println("to confirm...");
  display.println("(5s, NEXT=cancel)");
  display.display();

  String uid = readCardUidWithTimeout(CONFIRM_TIMEOUT_MS);

  if (uid == "") {
    display.clearDisplay();
    display.setCursor(0,0);
    display.println("Timed Out");
    display.display();
    beep(1,150);
    delay(1000);
    return false;
  }

  bool ok = verifyTeacherCard(uid, offeringId);

  display.clearDisplay();
  display.setCursor(0,0);
  if (ok) {
    display.println("Card Confirmed");
    display.display();
    beep(1,100);
    delay(600);
  } else {
    display.println("Unrecognized Card");
    display.display();
    beep(2,120);
    delay(1200);
  }

  return ok;
}
