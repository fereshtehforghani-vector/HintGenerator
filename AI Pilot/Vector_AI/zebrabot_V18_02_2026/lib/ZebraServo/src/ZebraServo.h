// #ifndef ZebraServo_h
// #define ZebraServo_h

// #include "Arduino.h"
// #include "ESP32Servo.h"
// // #include <ESP32Servo.h>  // Library for controlling servos on the ESP32

// // ZebraServo class: Abstraction for controlling a servo motor on a specified port
// class ZebraServo {
// public:
//   // Constructor: Takes a port number (1–7) and maps it to a specific GPIO pin
//   ZebraServo(int port);

//   // Initializes the servo by attaching it to the mapped GPIO pin
//   void begin();

//   // Moves the servo to the specified angle (0 to 180 degrees)
//   void run_angles(int angles);

// private:
//   int _port;           // Logical port number used for mapping to physical pins
//   int servoPin; 
//   int servoDuty;       // GPIO pin number used for servo signal
//   Servo myservo;       // Servo object from ESP32Servo library
// };

// #endif

#ifndef ZebraServo_h
#define ZebraServo_h

#include "Arduino.h"
#include "ESP32Servo.h"

// ZebraServo class: Abstraction for controlling a servo motor on a specified port
class ZebraServo {
public:
  // Constructor: Takes a port number (1–7) and maps it to a specific GPIO pin
  ZebraServo(int port);

  // Initializes the servo by attaching it to the mapped GPIO pin
  void begin();

  // Moves the servo to the specified angle (0 to 180 degrees)
  void run_angles(int angles);

private:
  int _port;           // Logical port number used for mapping to physical pins
  int servoPin; 
  int servoDuty;       // GPIO pin number used for servo signal
  Servo myservo;       // Servo object from ESP32Servo library
  
  // Static flag to track if timers have been allocated
  static bool timersAllocated;
};

#endif