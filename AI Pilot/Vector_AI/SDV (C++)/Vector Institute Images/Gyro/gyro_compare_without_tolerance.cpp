#include <Arduino.h>
#include <ZebraGyro.h>


ZebraGyro gyro(4, 2);
void setup() {
  Wire.begin();
  gyro.begin();
  gyro.resetYaw();
}
void loop() {
  gyro.update();
  if(gyro.getYaw() == 90.0) {} // Exact match unlikely!
}
