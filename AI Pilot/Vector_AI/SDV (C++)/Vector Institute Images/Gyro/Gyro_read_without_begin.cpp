#include <Arduino.h>
#include <ZebraGyro.h>
// MISTAKE 131
// Reading yaw without begin()
ZebraGyro gyro(4, 2);
void setup() {
  Wire.begin();
  float yaw = gyro.getYaw(); // Before begin()!
}
void loop() {}
