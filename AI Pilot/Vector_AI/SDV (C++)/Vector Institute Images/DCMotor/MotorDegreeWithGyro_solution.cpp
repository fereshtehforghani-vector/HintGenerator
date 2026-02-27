// Note: partial code shown — see full context in corresponding image
#include <Arduino.h>
#include <ZebraGyro.h>
#include "SMotor2.h"
#include "ZebraServo.h"

ZebraGyro gyro(7, 2);  // Port 7, interrupt pin 2
SMotor2 motor(2);
ZebraServo servo(1);

void setup() {
    Serial.begin(115200);
    delay(2000);
    Serial.println("Starting ZebraGyro...");
    gyro.begin();
    motor.begin();
    servo.begin();
}

void loop() {
    gyro.update();
    Serial.print("Yaw: ");
    Serial.println(gyro.getYaw());
    servo.run_angles(90);
    while (gyro.getYaw()<90)
    {
        gyro.update();
        servo.run_angles(45);
        motor.run_motor(40);
    }
    motor.stop_motor();
    delay(500);
    gyro.resetYaw();
}
