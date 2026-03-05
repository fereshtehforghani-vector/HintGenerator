#include <SMotor2.h>        // Library for controlling DC motors (custom for WRO kits)
#include <ESP32Servo.h>    // Library for controlling servos on ESP32
#include <ZebraTOF.h>      // Library for Time-of-Flight (ToF) distance sensors
#include <ZebraGyro.h>     // Library for gyroscope sensor
#include "Wire.h"          // I2C communication library

SMotor2 motor(1);           // Create motor object for motor channel 1
Servo myservo;             // Servo object for steering
int servoPin = 25;         // Servo is connected to GPIO pin 27
ZebraGyro gyro(7, 12);     // Gyroscope connected on port7
ZebraTOF front(4);         // Front ToF sensor at address 1
ZebraTOF right(3);         // Right ToF sensor at address 2
ZebraTOF left(2);          // Left ToF sensor at address 3

unsigned long lastSensorUpdate = 0;      // For timing sensor updates
const unsigned long sensorInterval = 50; // Update sensors every 50 ms
int turned = -2000;
int rightdist   ;                    // Right distance variable
int leftdist;                        // Left distance variable
int frontdist;                       // Front distance variable  
int x = 15;                          // Servo displacement value (not used in loop)
float offsetangle = 0;               // Offset reference angle for gyro navigation
const int buttonPin = 15;            // Push button pin for start/reset
int i = 0;                           // Encoder pulse counter
int count = 0;                       // Keeps track of number of turns made
int side = 0;                        // Side of robot movement: 1 = counter clockwise, 2 = clockwise
int target = 0;                      // Target yaw angle for turns
unsigned long last_time;             // Store last timestamp (unused now)
unsigned long curr_time = 0;         // Current timestamp (unused now)

#define enc 17                       // Encoder input pin
float yaw = 0;                       // Current yaw angle from gyro
int angle = 0;                       // Steering correction angle






// ---------------------- SETUP ----------------------
void setup() {
  Serial.begin(115200);        // Start serial monitor for debugging
  Wire.begin();                // Initialize I2C communication
  motor.begin();
  motor.stop_motor();       // Stop motor at the beginning

  // Initialize sensors
  
  front.begin();
  right.begin();
  left.begin();
  gyro.begin();

  pinMode(enc, INPUT_PULLUP);  // Encoder pin as input with pull-up resistor
  attachInterrupt(digitalPinToInterrupt(enc), wheel_pulse, RISING); // Count pulses

  myservo.attach(servoPin, 0, 3000); // Attach servo to pin, min/max pulse width

  pinMode(2, OUTPUT);          // Configure GPIO 2 as output (status LED)
  digitalWrite(2, HIGH);       // Turn LED ON (indicator)

  // Wait for button press before starting
  int buttonState = digitalRead(buttonPin);
  while (buttonState == 1) {   // Stay here until button is pressed
    buttonState = digitalRead(buttonPin);
  }
  delay(200);                  // Small delay after button press
}

// ---------------------- LOOP ----------------------
void loop() {
  int start = millis(); // Record loop start time

  // Read distances (limit between 0–1200 mm)
  rightdist = constrain(right.readDistance1(), 0, 1200);
  leftdist  = constrain(left.readDistance1(), 0, 1200);
  frontdist = constrain(front.readDistance1(), 0, 1200);

  // Update gyro orientation
  gyro.update();
  yaw = gyro.getYaw();

  // Movement logic depending on number of turns
  if (count >= 1 && count < 12) {
    // If already turned at least once but less than 12 times
    if (side == 1) {
      rforwardwall(yaw, rightdist); // Follow right wall
    } else {
      lforwardwall(yaw, leftdist);  // Follow left wall
    }
  } else if (count >= 12) {
    // After 12 turns, go straight for 6000 encoder ticks then stop
    i = 0;
    while (i < 2000) {
      gyro.update();
      yaw = gyro.getYaw();
      forward(yaw);
    }
    motor.stop_motor();       // Stop motors
    delay(1000000000);        // Effectively freeze the robot
  } else {
    forward(yaw);             // Default: go straight
  }

  // ---------- Turning decision ----------
  if (frontdist < 550 && frontdist > 0 && ((millis() - turned) > 3000)) { // Stop when at a certain distance from front wall
    motor.run_motor(60);              // Run motor to turn

   

    if (side == 1) { // If already following left
      count += 1;
      offsetangle -= 89;          // Turn left using gyro
      target = abs(offsetangle)-60;
      while (yaw > (target * -1)) {
        gyro.update();
        yaw = gyro.getYaw();
        myservo.write(60);        // Steer left
      }
    } else if (side == 2) { // If following right
      count += 1;
      offsetangle += 89;          // Turn right using gyro
      target = abs(offsetangle) - 50;
      while (yaw < target) {
        gyro.update();
        yaw = gyro.getYaw();
        myservo.write(130);       // Steer right
      }
    } else {
       rightdist = right.readDistance1();    // Re-check distances
    leftdist = left.readDistance1();
      // Decide based on walls
      if (rightdist < 800 && leftdist > 800) { // If wall is on right, turn left
        side = 1;
        count += 1;
        offsetangle -= 89;
        target = abs(offsetangle) - 50;
        while (yaw > (target * -1)) {
          gyro.update();
          yaw = gyro.getYaw();
          myservo.write(60);
        }
      } else if (leftdist < 800 && rightdist > 800) { // If wall is on left, turn right
        side = 2;
        count += 1;
        offsetangle += 89;
        target = abs(offsetangle) - 45;
        while (yaw < target) {
          gyro.update();
          yaw = gyro.getYaw();
          myservo.write(130);
        }
      }
    }
    turned = millis();
  }
}

// ---------------------- MOVEMENT FUNCTIONS ----------------------

// Move forward while correcting steering based on gyro
void forward(float g) {
  angle = (int)(0.8 * (g - (offsetangle))); // Steering correction
  int pos = 95 - angle;                     // Servo position
  myservo.write(pos);
  motor.run_motor(80);                  // Run motor forward
}

// Move forward while following a wall on the right
void rforwardwall(float g, int d) {
  float wallval = 0.08 * (d - 350);         // Correction factor based on distance
  angle = int(0.6 * (g - (offsetangle + wallval)));
  angle = constrain(angle, -10,10);
  int pos = 95 - angle;
  myservo.write(pos);
  pos = constrain(pos, 80,110);
  motor.run_motor(100);
}

// Move forward while following a wall on the left
void lforwardwall(float g, int d) {
  float wallval = 0.08* (d - 400);         // Correction factor based on distance
  angle = int(0.6 * (g - (offsetangle - wallval)));
  angle = constrain(angle, -10,10);
  int pos = 95 - angle;
  pos = constrain(pos, 80,110);
  myservo.write(pos);
  motor.run_motor(100);
}

// Interrupt: called whenever encoder detects a pulse
void wheel_pulse() {
  i++; // Increase encoder tick count
}






// // Write your code here#include <Arduino.h>
// #include "ZebraServo.h"
// #include "SMotor2.h"


// // Create a servo object on port 1 (GPIO 17)


// // SMotor2 motor2(2);
// ZebraServo myServo(4);
// // ZebraServo latch(3);
// SMotor2 motor(1);

// void setup() {
//   Serial.begin(115200);
//   // put your setup code here, to run once:
//   myServo.begin();
//   // latch.begin();
// motor.begin();
// // motor2.begin();

// }

// void loop() {
//   // put your main code here, to run repeatedly:
//   myServo.run_angles(100);                       /////steer straight
//   // latch.run_angles(120);
//   delay(500);
// // motor.move_degrees(300, 60);
// // motor2.move_degrees(1000, 50);
// // motor.stop_motor();
// delay(500);
// // Serial.println("done");

// // latch.run_angles(60);
// delay(500);
// motor.move_degrees(900,-60);
// // motor2.move_degrees(1000, 50);
// // motor.stop_motor();
// delay(500);

// myServo.run_angles(60);
// motor.move_degrees(320,-80);
// myServo.run_angles(100);
// motor.move_degrees(600,-80);
// myServo.run_angles(60);
// motor.move_degrees(270,-80);
// myServo.run_angles(100);
// motor.move_degrees(1450,-80);
// // latch.run_angles(120);
// delay(500);

// myServo.run_angles(100);
// motor.move_degrees(300,-60);
// delay(10000);

// // Serial.println("done Again");

// }


