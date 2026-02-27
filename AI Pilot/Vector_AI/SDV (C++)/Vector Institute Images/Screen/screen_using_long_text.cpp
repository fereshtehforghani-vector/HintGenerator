#include <Arduino.h>
#include <ZebraScreen.h>

ZebraScreen screen(0);
void setup() {
  Wire.begin();
  screen.begin();
  screen.write("This is a very long text that won't fit");
}
void loop() {}
