// Note: partial code shown — see full context in corresponding image
void forward(float g) {
    int gyro = 30;
    angle = (int)(0.8 * (gyro - (offsetangle)));  // Steering correction
    int pos = 95 - angle;                          // Servo position
    myservo.write(pos);
    motor.run_motor(1, 80);                        // Run motor forward
}
