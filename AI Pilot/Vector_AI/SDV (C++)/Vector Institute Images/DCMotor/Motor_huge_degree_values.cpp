#include <Arduino.h>
#include "SMotorPair.h"

SMotorPair motors(1, 2);
void setup() {
  motors.begin();
  motors.move_degrees(0, 50, 100000);
}
void loop() {}
