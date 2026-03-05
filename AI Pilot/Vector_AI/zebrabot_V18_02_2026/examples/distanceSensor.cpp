#include <Arduino.h>
#include "ZebraTOF.h"

ZebraTOF sensor(1); // Port 0 on multiplexer

void setup() {
  Serial.begin(115200);
  sensor.begin();
}

void loop() {
  Serial.println(sensor.readDistance());
  // delay(500);
}
