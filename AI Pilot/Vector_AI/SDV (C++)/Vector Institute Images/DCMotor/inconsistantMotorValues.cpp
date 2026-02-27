// write your code here
#include "Arduino.h"
#include "SMotor2.h"

SMotor2 motor(2);

void setup(){
    motor.begin();
}

void loop(){
    motor.move_degrees(2000,-6);
    delay(1000);
    motor.move_degrees(200,60);
    delay(1000);
}
