#include <Arduino.h>
#include <SMotor2.h>

SMotor2 motors(2);
int speed;
void setup() {
  motors.begin();
  motors.run_motor(speed); // Uninitialized speed!
}
void loop() {}
