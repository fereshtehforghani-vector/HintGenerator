// write your code here
SMotor2 motor(2);

void setup(){
    motor.begin();
}

void loop(){
    motor.move_degrees(500,-60);
    delay(1000);
    motor.move_degrees(500,60);
    delay(1000);
}
