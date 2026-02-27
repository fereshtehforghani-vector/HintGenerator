// write your code here
#include "Arduino.h"
#include "SMotor2.h"

SMotor2 motor(2);

int motorSpeed = 500;           // Speed of motor rotation
int angleClockwise = -60;       // Angle to rotate clockwise
int angleCounterClockwise = 60; // Angle to rotate counter-clockwise
int ledPin = 2;                 // Pin number for LED output
int delayTime = 500;            // Delay time in milliseconds

void setup(){
    pinMode(ledPin, OUTPUT);
    motor.begin();
}

void loop(){
    motor.move_degrees(motorSpeed, angleClockwise);
    digitalWrite(ledPin, HIGH);
    delay(delayTime);
    digitalWrite(ledPin, LOW);
    delay(delayTime);

    motor.move_degrees(motorSpeed, angleCounterClockwise);
    digitalWrite(ledPin, HIGH);
    delay(delayTime);
    digitalWrite(ledPin, LOW);
    delay(delayTime);
}
