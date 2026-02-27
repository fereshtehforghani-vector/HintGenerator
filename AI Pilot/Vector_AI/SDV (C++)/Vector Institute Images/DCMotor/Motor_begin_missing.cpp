#include <Arduino.h>
#include "SMotorPair.h"

SMotorPair motors(1, 2);
void setup() {
 
  motors.run(0, 50);
}
void loop() {

}
