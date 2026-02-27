// write your code here
#include "Arduino.h"
#include "SMotor2.h"

SMotor2 motor(2);

void setup(){
    pinMode(2, OUTPUT);
    motor.begin();
}

void loop(){
    motor.move_degrees(500,-60);
    digitalWrite(2,HIGH);
    delay(500);
    digitalWrite(2, LOW);
    delay(500);
    motor.move_degrees(500,60);
    digitalWrite(2, HIGH);
    delay(500);
    digitalWrite(2, LOW);
    delay(500);
    digitalWrite(2, HIGH);
    delay(500);
    digitalWrite(2, LOW);
}
