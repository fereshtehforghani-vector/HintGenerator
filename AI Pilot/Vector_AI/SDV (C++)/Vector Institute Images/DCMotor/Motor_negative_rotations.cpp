#include <Arduino.h>
#include "SMotorPair.h"

SMotorPair motors(1, 2);
void setup() {
  motors.begin();
  
}
void loop() {
  motors.move_rotations(0, 50, -1.0);
}
