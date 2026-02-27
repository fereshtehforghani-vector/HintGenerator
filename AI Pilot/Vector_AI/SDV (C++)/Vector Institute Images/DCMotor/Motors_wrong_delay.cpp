#include <Arduino.h>
#include "SMotorPair.h"

SMotorPair motors(1, 2);
void setup() { motors.begin(); }
void loop() {
  motors.run(0, 50);
  delay(5000); 
}
