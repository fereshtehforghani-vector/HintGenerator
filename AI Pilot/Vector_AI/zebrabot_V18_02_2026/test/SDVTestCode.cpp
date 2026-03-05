// #include "ZebraServo.h"

// ZebraServo servo1(1);
// // ZebraServo servo2(2);

// void setup(){
//     servo1.begin();
    
// }

// void loop(){
//     servo1.run_angles(0);
//     delay(1200);
//     servo1.run_angles(30);
//     delay(1200);
//     servo1.run_angles(60);
//     delay(1200);
//     servo1.run_angles(90);
//     delay(1200);
//     servo1.run_angles(120);
//     delay(1200);
//     servo1.run_angles(150);
//     delay(1200);
//     servo1.run_angles(180);
//     delay(1200);
    
    
    
    
// }






// // Write your code here#include <Arduino.h>
// #include "ZebraServo.h"
// #include "SMotor2.h"


// ZebraServo myServo(1);

// SMotor2 motor(3);

// void setup() {

//   myServo.begin();
 
// motor.begin();


// }

// void loop() {

//   myServo.run_angles(100);                       /////steer straight
 
// delay(500); 
// motor.move_degrees(900,-60);  /// go straight for 900 degrees

// delay(500);

// myServo.run_angles(60);
// motor.move_degrees(300,-80);    /// turn for 90 degrees using the steering
// myServo.run_angles(100);
// motor.move_degrees(600,-80);   ///going straight again
// myServo.run_angles(60);
// motor.move_degrees(300,-80);  /// turning for 90 degrees 
// myServo.run_angles(100);
// motor.move_degrees(1450,-80);  /// go straight again
// // latch.run_angles(120);
// delay(500);

// myServo.run_angles(100);
// motor.move_degrees(300,-60);
// delay(10000);



// }






































#include <SMotor2.h>        // Library for controlling DC motors (custom for WRO kits)
// #include <ESP32Servo.h>    // Library for controlling servos on ESP32
#include <ZebraTOF.h>      // Library for Time-of-Flight (ToF) distance sensors
#include <ZebraGyro.h>     // Library for gyroscope sensor
#include "Wire.h"          // I2C communication library
#include "ZebraServo.h"

SMotor2 motor(1);           // Create motor object for motor channel 1
ZebraServo myservo(3);             // Servo object for steering
ZebraGyro gyro(7, 12);     // Gyroscope connected on port7
ZebraTOF front(1);         // Front ToF sensor at address 1
// ZebraTOF right(4);         // Right ToF sensor at address 2
// ZebraTOF left(5); 
const int buttonPin = 15;  
int rightdist =0;                    // Right distance variable
int leftdist = 0;                        // Left distance variable
int frontdist = 0; 
float yaw = 0;                       // Current yaw angle from gyro
int angle = 0; 
float offsetangle = 0;  
int i = 0;                           // Encoder pulse counter
int count = 0;                       // Keeps track of number of turns made
int side = 0;                        // Side of robot movement: 1 = counter clockwise, 2 = clockwise
int target = 0;   

void setup(){


Serial.begin(115200);
front.begin();
// left.begin();
// right.begin();
motor.begin();
myservo.begin();
gyro.begin();


pinMode(2, OUTPUT);          // Configure GPIO 2 as output (status LED)
  digitalWrite(2, HIGH);       // Turn LED ON (indicator)

//   Wait for button press before starting
  int buttonState = digitalRead(buttonPin);
  while (buttonState == 1) {   // Stay here until button is pressed
    buttonState = digitalRead(buttonPin);
  }
  delay(200); 

}


// Move forward while correcting steering based on gyro
void forward(float g) {
  angle = (int)(0.8 * (g - (offsetangle))); // Steering correction
  int pos = 95 - angle;                     // Servo position
  myservo.run_angles(pos);
  motor.run_motor(30);                  // Run motor forward
}
// Move forward while following a wall on the right
// void rforwardwall(float g, int d) {
//   float wallval = 0.08 * (d - 350);         // Correction factor based on distance
//   angle = int(0.6 * (g - (offsetangle + wallval)));
//   angle = constrain(angle, -10,10);
//   int pos = 95 - angle;
//   myservo.run_angles(pos);
//   pos = constrain(pos, 80,110);
//   motor.run_motor(100);
// }

void loop(){

     int start = millis(); // Record loop start time

  // Read distances (limit between 0–1200 mm)
  // rightdist = constrain(right.readDistance1(), 0, 1200);
//   leftdist  = constrain(left.readDistance1(), 0, 1200);
  frontdist = constrain(front.readDistance1(), 0, 1200);

  // Update gyro orientation
  gyro.update();
  yaw = gyro.getYaw();
// Serial.print(right.readDistance1());
// Serial.println(front.readDistance1());
   forward(yaw);
    if (frontdist<500){
      motor.stop_motor();
      // delay(500);
 offsetangle -= 90;          // Turn left using gyro
      target = abs(offsetangle)-75;
      while (yaw > (target * -1)) {
        gyro.update();
        yaw = gyro.getYaw();
        myservo.run_angles(60);  
          motor.run_motor(30);       // Steer left
      }
    }
}

