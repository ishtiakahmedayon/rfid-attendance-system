// Return codes for readCard() are defined in rfid_esp32.ino (READCARD_BACK,
// READCARD_SCANNED, READCARD_TIMEOUT) so they're visible to every tab.

// Waits up to `ms` milliseconds, but keeps checking BTN_NEXT the whole time.
// Returns true immediately if NEXT is pressed during the wait.
bool waitOrButton(unsigned long ms) {
  unsigned long start = millis();
  while (millis() - start < ms) {
    if (buttonPressed(BTN_NEXT)) {
      return true;
    }
  }
  return false;
}

// pollWindowMs: if no card shows up within this many milliseconds,
// return READCARD_TIMEOUT so the caller can poll the server and then
// call readCard() again. Pass 0 to wait indefinitely for a card (used
// when there's no active session to watch, e.g. plain card testing).
int readCard(unsigned long pollWindowMs){

  uint8_t uid[7];
  uint8_t uidLength;

  unsigned long waitStart = millis();

  // Waits (blocking, in small 50ms chunks) until a card is presented,
  // NEXT is pressed, or the poll window elapses
  while(true){
    if(buttonPressed(BTN_NEXT)){
      return READCARD_BACK;
    }

    bool success = nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, uid, &uidLength, 50);
    if(success){
      break;
    }

    if (pollWindowMs > 0 && millis() - waitStart >= pollWindowMs) {
      return READCARD_TIMEOUT;
    }
  }

  Serial.print("Card detected. UID: ");
  for (uint8_t i = 0; i < uidLength; i++) {
    if (uid[i] < 0x10) Serial.print("0");
    Serial.print(uid[i], HEX);
    Serial.print(" ");
  }


  beep(1, 100);
  digitalWrite(LED_RED, HIGH);
  bool backPressed = waitOrButton(300);   // interruptible pause
  digitalWrite(LED_RED, LOW);
  

  String uidString = "";
  for (int i = 0; i < uidLength; i++) {
    if (uid[i] < 0x10) uidString += "0";
    uidString += String(uid[i], HEX);
  }
  uidString.toUpperCase();
  Serial.println(uidString);

  sendAttendance(uidString);   // shows name/status on OLED, holds it ~1-1.5s

  return backPressed ? READCARD_BACK : READCARD_SCANNED;
}
