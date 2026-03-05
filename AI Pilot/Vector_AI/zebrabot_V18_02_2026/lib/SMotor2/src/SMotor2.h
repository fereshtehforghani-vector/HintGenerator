#ifndef SMOTOR2_H
#define SMOTOR2_H

#include <Arduino.h>
#include <Wire.h>

class SMotor2 {
  public:
    SMotor2(int port);           // Constructor with port selection
    void begin();                // Initialize motor
    void run_motor(int power);   // Run motor at power (-100 to 100)
    void stop_motor();           // Stop motor
    void move_degrees(int degrees, int initial_speed);  // Move by degrees
    void move_rotations(float rotations, int initial_speed); // Move by rotations
    void move_time(float time, int initial_speed);  // Run for time (seconds)

    static volatile int tickCount; // Public tick counter for encoder
    static void wheel_pulse();     // ISR for encoder pulses

  private:
    int _port;
    int PWM, dirc, enc;
    uint8_t _pwmChannel;          // Store PWM channel
    int _ticksPerRev = 610;       // Encoder ticks per revolution
};

#endif