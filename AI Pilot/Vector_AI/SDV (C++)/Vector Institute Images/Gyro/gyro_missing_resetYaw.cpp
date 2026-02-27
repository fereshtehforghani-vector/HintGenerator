#include <Arduino.h>
#include <ZebraGyro.h>

ZebraGyro gyro(7, 2);
void setup() {
  Wire.begin();
  gyro.begin();
 
  while(gyro.getYaw() < 90) {
    // statements
  }
}
void loop() {}
