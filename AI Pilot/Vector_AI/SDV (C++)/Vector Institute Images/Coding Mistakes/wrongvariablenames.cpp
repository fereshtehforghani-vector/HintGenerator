// write your code here
#include "Arduino.h"
#include "SMotor2.h"

SMotor2 motor(2);

int a = 500;
int b = -60;
int c = 60;
int d = 2;
int x = 500;

void setup(){
    pinMode(d, OUTPUT);
    motor.begin();
}

void loop(){
    motor.move_degrees(a,b);
    digitalWrite(d,HIGH);
    delay(x);
    digitalWrite(d, LOW);
    delay(x);
    motor.move_degrees(a,c);
    digitalWrite(d, HIGH);
    delay(x);
    digitalWrite(d, LOW);
    delay(x);
}
