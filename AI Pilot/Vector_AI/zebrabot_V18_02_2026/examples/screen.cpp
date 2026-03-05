#include <Arduino.h>
#include <ZebraScreen.h>

// Screen is connected through I2C multiplexer at port 1
ZebraScreen screen(0);

void setup() {
  Serial.begin(115200);
  Serial.println("Initializing ZebraScreen...");

  // Initialize the OLED
  screen.begin();

  // Show startup message
  screen.write("Hello Zebra!");
  delay(2000);

  // Clear and prepare
  screen.clear();
  screen.writeLine(2, "ZebraScreen Test");
}

void loop() {
  static int counter = 0;

  // Update line 1 with counter value
  screen.writeLine(3, "Counter: " + String(counter));

  counter++;
  delay(1000);
}
