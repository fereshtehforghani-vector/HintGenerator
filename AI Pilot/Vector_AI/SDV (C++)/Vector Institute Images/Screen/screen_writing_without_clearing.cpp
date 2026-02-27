#include <Arduino.h>
#include <ZebraScreen.h>

ZebraScreen screen(0);
void setup() {
  Wire.begin();
  screen.begin();
}
void loop() {
  screen.write("Test"); // Overlaps previous!
  delay(1000);
}
