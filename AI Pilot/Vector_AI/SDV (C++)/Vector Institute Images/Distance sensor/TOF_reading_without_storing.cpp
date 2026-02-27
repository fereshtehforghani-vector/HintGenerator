#include <Arduino.h>
#include <ZebraTOF.h>

ZebraTOF tof(2);
void setup() {
  Wire.begin();
  tof.begin();
}
void loop() {
  tof.readDistance(); // Result ignored!
  delay(100);
}
