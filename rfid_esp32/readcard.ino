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
bool readCard(){

  uint8_t uid[7];
  uint8_t uidLength;

  // Waits (blocking) until a card is presented or the read times out
  while(true){
    if(buttonPressed(BTN_NEXT)){
      return true;
    }
    bool success = nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, uid, &uidLength, 50);
    if(success){
      break;
    }
  }

  Serial.print("Card detected. UID: ");
  for (uint8_t i = 0; i < uidLength; i++) {
    if (uid[i] < 0x10) Serial.print("0");
    Serial.print(uid[i], HEX);
    Serial.print(" ");
  }


  // beep(1, 100);
  digitalWrite(LED_PIN, HIGH);
  bool backPressed = waitOrButton(300);   // interruptible pause
  digitalWrite(LED_PIN, LOW);
  

  String uidString = "";
  for (int i = 0; i < uidLength; i++) {
    if (uid[i] < 0x10) uidString += "0";
    uidString += String(uid[i], HEX);
  }
  uidString.toUpperCase();
  Serial.println(uidString);

  sendAttendance(uidString);   // shows name/status on OLED, holds it ~1-1.5s


  return backPressed;   // <-- MUST be this, not "return true;"
}