#ifndef SMotorPair_h
#define SMotorPair_h

#include "Arduino.h"
#include "SMotor2.h"


// SMotorPair manages a pair of motors using the SMotor2 class.
// It enables coordinated movement of left and right motors with simple or PID control.
class SMotorPair {
public:
    // Constructor to initialize left and right motor ports
    SMotorPair(int left_port, int right_port);

    // Initializes the motors and sets up encoders
    void begin();

    // Stops both motors
    void stop_motors();

    // void move_simple(int steer, int pace, float distance);
    // void move_PID_simple(int steer, int pace, float distance);
    
    // Moves based on number of encoder degrees, with steering and initial speed
    void move_degrees(int steer, int initial_speed, float degrees);

    // Moves based on number of wheel rotations, with steering and initial speed
    void move_rotations(int steer, int initial_speed, float rotations);

    // Moves for a specified amount of time (in seconds), with steering and initial speed
    void move_time(int steer, int initial_speed, float time_seconds);

    void run_until(int steer, int initial_speed, bool (*stop_condition)());
    void run(int steer, int initial_speed);
private:
    // Motor port IDs
    int _left_port, _right_port;

    // Motor objects
    SMotor2 left_motor;
    SMotor2 right_motor;

    // Encoder pulse counters for each motor and the robot as a whole
    volatile long left_wheel_pulse_count;
    volatile long right_wheel_pulse_count;
    volatile long robot_pulse_count;

    // Motor pace and speed variables for left and right
    int left_pace, right_pace;
    int leftSpeed, rightSpeed; 

    // Number of encoder ticks per full motor revolution
    int _ticksPerRev;
};

#endif
