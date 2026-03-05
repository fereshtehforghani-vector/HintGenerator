#include "ZebraServo.h"
#include "ZebraScreen.h"

ZebraServo servo(1);
ZebraScreen screen(0);

void setup(){
    servo.begin();
    screen.begin();
}

void loop(){
    servo.run_angles(45);
    delay(1000);
    servo.run_angles(90);
    delay(1000);
    servo.run_angles(180);
    delay(1000);
    screen.clear();
    screen.writeLine(1,"Zebra");
}