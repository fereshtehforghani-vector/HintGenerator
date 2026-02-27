#include <Arduino.h>
#include <ZebraScreen.h>

void setup() {}
void loop() {
  Wire.begin(); // Should be in setup!
  ZebraScreen screen(0);
  screen.begin();
  screen.write("Hello");
}
