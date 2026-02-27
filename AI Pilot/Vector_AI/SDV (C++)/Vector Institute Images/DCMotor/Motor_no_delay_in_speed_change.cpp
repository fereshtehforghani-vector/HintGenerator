#include <Arduino.h>
#include <SMotor2.h>
// MISTAKE 118
// Speed changes too frequently
SMotor2 motor(1);
void setup() { motor.begin(); }
void loop() {
  motor.run_motor(30);
  motor.run_motor(60);
  motor.run_motor(90); //No delay between changes!
}
