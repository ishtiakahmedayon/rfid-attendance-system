#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Adafruit_PN532.h>

#define SCREEN_WIDTH  128
#define SCREEN_HEIGHT 64
#define OLED_RESET    -1
#define OLED_ADDR     0x3C   // change to 0x3D if your I2C scan found that address instead

#define PN532_IRQ   4
#define PN532_RESET 5

#define BUZZER_PIN  25
#define LED_PIN     2
#define BTN_NEXT 32
#define BTN_SELECT 33

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
Adafruit_PN532 nfc(PN532_IRQ, PN532_RESET);

const char *menuItems[] = {
  "Read Card",
  "Write Card",
  "About"
};

int selected = 0;
const int menuSize = 3;

void setup() {

  Serial.begin(115200);
  delay(1000);

  pinMode(BTN_NEXT, INPUT_PULLUP);
  pinMode(BTN_SELECT, INPUT_PULLUP);
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);

  digitalWrite(LED_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);

  Serial.println("========== RFID MENU START ==========");

  // I2C
  // Wire.begin();
  Wire.begin(21, 22);   // SDA, SCL
  delay(100);

  // ---------- OLED ----------
  display.begin(SSD1306_SWITCHCAPVCC, 0x3C);

  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);

  Serial.println("[OK] OLED Initialized");

  // ---------- PN532 ----------
  nfc.begin();

  uint32_t version = nfc.getFirmwareVersion();

  if (!version) {
    Serial.println("[ERROR] PN532 NOT FOUND");

    display.clearDisplay();
    display.setCursor(0,0);
    display.println("PN532 NOT FOUND");
    display.display();

    while (1);
  }

  Serial.print("[OK] Firmware: ");
  Serial.print((version >> 16) & 0xFF);
  Serial.print(".");
  Serial.println((version >> 8) & 0xFF);

  nfc.SAMConfig();

  Serial.println("[OK] PN532 Ready");

  // ---------- MENU ----------
  drawMenu();

  Serial.println("[OK] Menu Ready");
}

void loop() {
  // if (buttonPressed(BTN_NEXT)) {

  //   selected++;

  //   if (selected >= menuSize)
  //     selected = 0;

  //   drawMenu();
  // }
  drawMenu();          // return to menu


  if (buttonPressed(BTN_SELECT)) {

    // switch (selected) {

    //   case 0:
    //     ReadCard();
    //     break;

    //   case 1:
    //          // dummy function
    //     break;

    //   case 2:
    //          // dummy function
    //     break;
    // }
    if(selected == 0){
      readCardMenu();
    }

    drawMenu();


  }
}

void drawMenu() {

  if (buttonPressed(BTN_NEXT)) {

    selected++;

    if (selected >= menuSize)
      selected = 0;
  }

  display.clearDisplay();
  display.setCursor(0,0);
  display.println("MAIN MENU");

  for (int i = 0; i < menuSize; i++) {

    display.setCursor(0,16 + i*12);

    if (i == selected)
      display.print("> ");
    else
      display.print("  ");

    display.println(menuItems[i]);
  }

  display.display();
}

void drawSubMenu() {
  if(buttonPressed(BTN_NEXT)) {
    drawMenu();
  }

  display.clearDisplay();
  display.setCursor(0, 0);
  display.println("Tap the card to read....");
  display.display();
  delay(1000);

  // ReadCard();
}

bool buttonPressed(int pin) {

  if (digitalRead(pin) == LOW) {

    delay(20);              // debounce

    if (digitalRead(pin) == LOW) {

      while (digitalRead(pin) == LOW);   // wait until released

      delay(20);

      return true;
    }
  }

  return false;
}
void beep(int times, int durationMs) {
  for (int i = 0; i < times; i++) {
    digitalWrite(BUZZER_PIN, HIGH);
    delay(durationMs);
    digitalWrite(BUZZER_PIN, LOW);
    if (i < times - 1) delay(durationMs);
  }
}
void readCardMenu() {

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
    if (readCard()) {
      return;
    }

    delay(20);
  }
}


