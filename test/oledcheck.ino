#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64

#define OLED_SDA 21
#define OLED_SCL 22
#define OLED_ADDR 0x3C

Adafruit_SSD1306 display(
  SCREEN_WIDTH,
  SCREEN_HEIGHT,
  &Wire,
  -1
);

void setup() {
  Serial.begin(115200);

  // Start I2C
  Wire.begin(OLED_SDA, OLED_SCL);

  // Initialize OLED
  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    Serial.println("OLED not found!");
    while (1);
  }

  Serial.println("OLED found!");

  // Clear screen
  display.clearDisplay();

  // Text settings
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);

  display.println("ESP32 OLED TEST");
  display.println("----------------");
  display.println("OLED: OK");
  display.println("ESP32: OK");
  display.println("SDA: GPIO 21");
  display.println("SCL: GPIO 22");

  // Show everything
  display.display();
}

void loop() {
}
