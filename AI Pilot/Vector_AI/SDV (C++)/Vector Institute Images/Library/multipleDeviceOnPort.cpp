// Note: partial code shown — see full context in corresponding image
#include <Arduino.h>
#include <ZebraGyro.h>
#include "SMotor2.h"
#include "ZebraServo.h"
#include "ZebraColour.h"
#include "ZebraTOF.h"

ZebraGyro gyro(7, 2);  // Port 7, interrupt pin 2
ZebraTOF distanceSensor(1);
SMotor2 motor(2);
SMotor2 motor2(2);
ZebraServo servo(1);
ZebraColour colorsensor(1);
