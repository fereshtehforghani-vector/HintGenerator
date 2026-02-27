#include <Arduino.h>
#include "SMotorPair.h"

SMotorPair motors(0, 0); 
void setup() {
  motors.begin();
  motors.run(0, 50);
}
void loop() {}
