#include <Arduino.h>
#include <ZebraScreen.h>

ZebraScreen screen(0);
void setup() {
  Wire.begin();
  screen.begin();
  screen.writeLine(10, "Text"); // Line 10 doesn't exist!
}
void loop() {}
