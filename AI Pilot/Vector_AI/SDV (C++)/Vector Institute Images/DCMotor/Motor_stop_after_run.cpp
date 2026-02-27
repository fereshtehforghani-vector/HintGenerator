#include <Arduino.h>
#include <SMotorPair.h>

SMotorPair motors(1, 2);
void setup() {
  motors.begin();
  motors.run(0, 50);
  motors.stop_motors(); // Stops immediately!
}
void loop() {}
