// Note: partial code shown — see full context in corresponding image
void loop() {
  // Move servo to 60 degrees
  Serial.println("Servo -> 60°");
  myServo.run_angles(600);

  // Move motor forward
  Serial.println("Motor -> Forward 1000 degrees");
  motor.move_degrees(1000, 50);
  delay(500);
  Serial.println("Done!");
}
