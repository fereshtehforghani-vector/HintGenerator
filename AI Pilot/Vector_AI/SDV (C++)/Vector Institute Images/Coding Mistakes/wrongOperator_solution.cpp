// Note: partial code shown — see full context in corresponding image
void loop() {
  // Turn right until 90 degrees
  Serial.println("Turning to 90 degrees...");

  gyro.update();
  while (gyro.getYaw() < 90) {
    gyro.update();
    leftMotor.run_motor(50);   // Left motor forward
    rightMotor.run_motor(-50); // Right motor backward

    Serial.print("Current angle: ");
    Serial.println(gyro.getYaw());
    delay(50);
  }
}
