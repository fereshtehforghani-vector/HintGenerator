#include <Arduino.h>
#include "SMotorPair.h"

SMotorPair motors(1, 2);
void setup() {
  motors.begin();
  motors.move_time(0, -200, 2.0); 
}
void loop() {}
