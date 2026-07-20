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

// Returns true if the user pressed NEXT (wants to go back to the menu)
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

  display.clearDisplay();
  display.setCursor(0,20);
  display.println("Card Detected");
  display.print("UID:");

  for (uint8_t i = 0; i < uidLength; i++) {
    if (uid[i] < 0x10) {
      Serial.print("0");
      display.print("0");
    }
    Serial.print(uid[i], HEX);
    Serial.print(" ");

    display.print(uid[i], HEX);
    display.print(" ");
  }

  Serial.println();
  display.display();

  beep(1, 100);
  digitalWrite(LED_PIN, HIGH);

  bool backPressed = waitOrButton(300);   // LED-on hold, now interruptible
  digitalWrite(LED_PIN, LOW);

  if (!backPressed) {
    backPressed = waitOrButton(1000);     // debounce window, now interruptible
  }

  display.display();

  return backPressed;
}