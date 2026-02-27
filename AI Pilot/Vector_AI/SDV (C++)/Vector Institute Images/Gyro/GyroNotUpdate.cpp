#include <Arduino.h>
#include <ZebraGyro.h>

ZebraGyro gyro(7, 2);  // Port 0, interrupt pin 2

void setup() {
    Serial.begin(115200);
    delay(2000);
    Serial.println("Starting ZebraGyro...");
    gyro.begin();
}

void loop() {

    Serial.print("Yaw: ");
    Serial.println(gyro.getYaw());
    delay(500);
}
