void readCardMenuTest() {

  display.clearDisplay();
  display.setCursor(0,0);
  display.println("Tap card...");
  display.println("NEXT = Back");
  display.display();

  while (true) {

    // Return to menu anytime
    if (buttonPressed(BTN_NEXT)) {
      return;
    }

    // readCard() now returns true if NEXT was pressed either while
    // waiting for a card, or during the post-read LED/debounce pause
    if (readCardTest()) {
      return;
    }

    delay(20);
  }
}

// Returns true if the user pressed NEXT (wants to go back to the menu)
bool readCardTest(){

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

  String uidString = "";

  for (int i = 0; i < uidLength; i++)
  {
      if (uid[i] < 0x10)
          uidString += "0";
        
      uidString += String(uid[i], HEX);
  }

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