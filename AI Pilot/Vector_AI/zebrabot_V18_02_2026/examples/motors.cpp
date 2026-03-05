#include <Arduino.h>
#include "SMotor2.h"
#include "ZebraServo.h"


// Create servo on port 3 and motor on port 1
ZebraServo myServo(3);
SMotor2 motor(1);


void setup() {
  Serial.begin(115200);
  delay(1000); // Give serial time to initialize
  
  Serial.println("Initializing motor and servo...");
  
  // Initialize motor first, then servo
  motor.begin();
  myServo.begin();
  
  Serial.println("Initialization complete!");
  // color.begin();
  delay(500);
}

void loop() {
  // Move servo to 60 degrees
  Serial.println("Servo -> 60°");
  myServo.run_angles(60);
  
  // Move motor forward
  Serial.println("Motor -> Forward 1000 degrees");
  motor.move_degrees(1000, 50);
  delay(500);
  Serial.println("Done!");
  
  // Move servo to 120 degrees
  Serial.println("Servo -> 120°");
  myServo.run_angles(120);
  
  // Move motor backward
  Serial.println("Motor -> Backward 1000 degrees");
  motor.move_degrees(1000, -50);
  delay(500);
  Serial.println("Done Again!");
  
  // delay(1000); // Pause before repeating
}
