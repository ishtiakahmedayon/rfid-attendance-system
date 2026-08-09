#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Adafruit_PN532.h>
#include <ArduinoJson.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>

const char* ssid = "Green_House";
const char* password = "@greenhouse";

const char* SERVER = "https://rfid-attendance-system-c42q.onrender.com";
const int HTTP_TIMEOUT_MS = 20000;
const int HTTP_RETRIES = 3;

// Must match DEVICE_API_KEY on the server (config.py / Render env var).
const char* API_KEY = "dev-only-change-me";

// How often (ms) the device checks the server for a remotely
// started/ended session. 3-4s keeps things responsive without hammering
// the server or the WiFi radio.
const unsigned long POLL_INTERVAL_MS = 3500;
unsigned long lastPollMs = 0;

// Return codes for readCard() (defined here, in the main .ino, so they're
// guaranteed to be visible to every other tab -- the Arduino IDE
// concatenates the main sketch file first, then the other tabs
// alphabetically, so a #define living in readcard.ino wouldn't be seen
// by code above it in this file).
#define READCARD_BACK     1   // NEXT pressed -> caller should exit
#define READCARD_SCANNED  2   // card scanned + processed, keep scanning
#define READCARD_TIMEOUT  3   // no card yet, but pollWindowMs elapsed so the
                               // caller can check the server (e.g. did the
                               // teacher end the session remotely?) before
                               // waiting for a card again

#define MAX_OFFERINGS 20
String offeringLabels[MAX_OFFERINGS];   // shown on screen, e.g. "ICT2207 (B24)"
long offeringIds[MAX_OFFERINGS];        // sent to /start_session
int offeringCount = 0;
int offeringSelected = 0;
int currentSession = -1;

String currentCourse = "";

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
  "Create Session",
  "Read Card Test",
};

int selected = 0;
const int menuSize = 2;

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

  connectWiFi();
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
  // While sitting idle at the main menu, periodically check whether a
  // teacher has remotely started a session from the dashboard. If so,
  // jump straight into attendance-taking for that course -- no menu
  // navigation needed on the device.
  if (millis() - lastPollMs >= POLL_INTERVAL_MS) {
    lastPollMs = millis();
    checkForRemoteStart();
  }

  drawMenu();          // return to menu


  if (buttonPressed(BTN_SELECT)) {
    if(selected == 0){
      offeringMenu();
      
    }else if(selected == 1){
      readCardMenuTest();
    }
    // else if(selected==2){
    //   readCardMenu();
    // }

    drawMenu();


  }
}

// Checks the server for a remotely started session and, if there is one
// this device doesn't already know about, jumps straight into
// attendance-taking for it.
void checkForRemoteStart() {
  long remoteSessionId = -1;
  long remoteOfferingId = -1;
  String remoteCourseCode = "";
  bool requestOk = false;

  bool active = pollDeviceCommand(remoteSessionId, remoteOfferingId, remoteCourseCode, requestOk);

  if (active && remoteSessionId != currentSession) {
    currentSession = remoteSessionId;
    currentCourse = remoteCourseCode;

    display.clearDisplay();
    display.setCursor(0,0);
    display.println("Remote Session");
    display.println("Started");
    display.println(currentCourse);
    display.display();
    beep(1,100);
    delay(800);

    readCardMenu();
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

  while (true) {

    bool sessionActive = (currentSession != -1);

    display.clearDisplay();
    display.setCursor(0,0);
    display.println("Tap card...");
    display.println(sessionActive ? "NEXT = End Session" : "NEXT = Back");
    display.display();

    // Only poll while there's an active session to watch -- no point
    // spending network calls when this is just idle card testing.
    unsigned long pollWindow = sessionActive ? POLL_INTERVAL_MS : 0;

    int result = readCard(pollWindow);

    if (result == READCARD_BACK) {
      if (sessionActive) {
        sendEndSession(currentSession);
        currentSession = -1;
        currentCourse = "";
      }
      return;
    }

    if (result == READCARD_TIMEOUT) {
      // No card yet -- check whether the teacher ended (or swapped)
      // the session remotely from the dashboard.
      long remoteSessionId = -1;
      long remoteOfferingId = -1;
      String remoteCourseCode = "";
      bool requestOk = false;

      bool active = pollDeviceCommand(remoteSessionId, remoteOfferingId, remoteCourseCode, requestOk);

      // Only act on a successful response -- a failed/flaky request
      // should never be treated as "the session ended".
      if (requestOk && (!active || remoteSessionId != currentSession)) {
        display.clearDisplay();
        display.setCursor(0,0);
        display.println("Session Ended");
        display.println("(from dashboard)");
        display.display();
        beep(2,80);
        delay(1200);

        currentSession = -1;
        currentCourse = "";
        return;
      }

      continue;
    }

    // READCARD_SCANNED -- keep scanning for the next card
    delay(20);
  }
}

//conecting wifi 

void connectWiFi()
{
    WiFi.begin(ssid, password);

    display.clearDisplay();
    display.setCursor(0,0);
    display.println("Connecting WiFi");
    display.display();

    while(WiFi.status()!=WL_CONNECTED)
    {
        delay(500);
        Serial.print(".");
    }

    Serial.println("\nWiFi Connected");

    display.clearDisplay();
    display.println("WiFi Connected");
    display.display();
    delay(1000);
}


// offering menu (course offerings, not just courses — same course
// can have separate offerings for different batches/years)
// OLED only fits 3-4 rows, so this scrolls one offering at a time
// via NEXT rather than listing them all at once.

void offeringMenu()
{
    if (!fetchOfferings()) {
        display.clearDisplay();
        display.println("No Offerings Found");
        display.display();
        delay(1500);
        return;
    }

    offeringSelected = 0;
    int totalItems = offeringCount + 1;   // +1 for "Exit"

    while (true) {
        display.clearDisplay();
        display.setCursor(0,0);
        display.println("Select Offering:");

        // Show up to 3 offerings at a time, scrolled around offeringSelected
        int visibleRows = 3;
        int startIdx = offeringSelected;
        if (startIdx > offeringCount - visibleRows) startIdx = offeringCount - visibleRows;
        if (startIdx < 0) startIdx = 0;

        int row = 0;
        for (int i = startIdx; i < offeringCount && row < visibleRows; i++, row++) {
            display.setCursor(0, 16 + row*12);
            if (i == offeringSelected) display.print("> ");
            else display.print("  ");
            display.println(offeringLabels[i]);
        }

        // "Exit" shown only when scrolled to the end
        if (offeringSelected == offeringCount) {
            display.setCursor(0, 16 + row*12);
            display.println("> Exit");
        }

        display.display();

        if (buttonPressed(BTN_NEXT)) {
            offeringSelected++;
            if (offeringSelected >= totalItems) offeringSelected = 0;
        }

        if (buttonPressed(BTN_SELECT)) {
            if (offeringSelected == offeringCount) {
                return;   // "Exit" chosen — back to main menu, no session started
            }

            createSession(offeringIds[offeringSelected], offeringLabels[offeringSelected]);
            if (currentSession != -1) {
                readCardMenu();
            }
            return;
        }
    }
}
