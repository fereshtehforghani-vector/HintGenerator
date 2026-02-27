#include <Arduino.h>
#include <ZebraScreen.h>

ZebraScreen screen(0);
void setup() {
  Wire.begin();
  screen.begin();
  screen.write("Line1");
  screen.write("Line2"); // Overlaps!
}
void loop() {}
