#include <Arduino.h>
#include <ZebraGyro.h>

ZebraGyro gyro(4, 2);
void setup() {
  Wire.begin();
  gyro.begin();
}
void loop() {
  gyro.resetYaw(); // Resets every loop!
  float yaw = gyro.getYaw();
}
