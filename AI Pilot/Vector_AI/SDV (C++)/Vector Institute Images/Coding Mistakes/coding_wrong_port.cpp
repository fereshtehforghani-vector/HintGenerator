#include <Arduino.h>
#include <ZebraColour.h>
#include <ZebraTOF.h>


ZebraTOF tof(2);
ZebraColour color(2); // Same port!
void setup() {
  Wire.begin();
  tof.begin();
  color.begin(); // Conflict!
}
void loop() {}
