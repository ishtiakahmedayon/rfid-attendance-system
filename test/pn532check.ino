#include <Wire.h>
#include <Adafruit_PN532.h>

#define SDA_PIN 21
#define SCL_PIN 22


Adafruit_PN532 nfc(-1, -1, &Wire);

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println();
  Serial.println("================================");
  Serial.println("ESP32 + PN532 RFID TEST");
  Serial.println("================================");

  // Start I2C
  Wire.begin(SDA_PIN, SCL_PIN);

  Serial.println("Initializing PN532...");

  nfc.begin();

  // Check PN532 firmware
  uint32_t versiondata = nfc.getFirmwareVersion();

  if (!versiondata) {
    Serial.println("ERROR: PN532 not found!");
    Serial.println("Check:");
    Serial.println("1. Wiring");
    Serial.println("2. PN532 I2C mode");
    Serial.println("3. VCC and GND");
    while (1) {
      delay(1000);
    }
  }

  Serial.println("PN532 found!");

  Serial.print("Firmware: ");
  Serial.print((versiondata >> 24) & 0xFF);
  Serial.print(".");
  Serial.println((versiondata >> 16) & 0xFF);


  nfc.SAMConfig();

  Serial.println("PN532 ready.");
  Serial.println();
  Serial.println("Place an RFID/NFC card near the PN532...");
}

void loop() {

  uint8_t uid[7];
  uint8_t uidLength;

  // Wait for an ISO14443A card
  bool success = nfc.readPassiveTargetID(
    PN532_MIFARE_ISO14443A,
    uid,
    &uidLength
  );

  if (success) {

    Serial.println();
    Serial.println("******** CARD DETECTED ********");

    Serial.print("UID: ");

    for (uint8_t i = 0; i < uidLength; i++) {

      if (uid[i] < 0x10) {
        Serial.print("0");
      }

      Serial.print(uid[i], HEX);

      if (i < uidLength - 1) {
        Serial.print(" ");
      }
    }

    Serial.println();

    Serial.print("UID Length: ");
    Serial.print(uidLength);
    Serial.println(" bytes");

    Serial.println("********************************");

    // Prevent the same card from being printed continuously
    delay(1500);
  }

  delay(100);
}
