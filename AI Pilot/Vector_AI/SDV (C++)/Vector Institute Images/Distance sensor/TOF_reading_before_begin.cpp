#include <Arduino.h>
#include <ZebraTOF.h>
// MISTAKE 127
// Reading before begin()
ZebraTOF tof(2);
void setup() {
  Wire.begin();
  int d = tof.readDistance(); // Before begin()!
  tof.begin();
}
void loop() {}
