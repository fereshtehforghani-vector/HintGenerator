#include <Arduino.h>
#include "SMotorPair.h"

SMotorPair motors(1, 2);
void setup() {
  motors.begin();
  motors.move_time(50, 2.0, 0); // Parameters swapped!
}
void loop() {}
