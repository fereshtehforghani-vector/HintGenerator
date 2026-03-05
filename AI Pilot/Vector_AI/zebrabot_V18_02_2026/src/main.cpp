// write your code here

#include <Arduino.h>
#include "SMotor2.h"
#include "SMotorPair.h"

SMotorPair motors(2, 1);   // Left =2, Right =1

// Robot geometry
const float WHEEL_RADIUS = 0.0312;     // meters
const float WHEEL_BASE   = 0.105;      // meters
const int TICKS_PER_REV  = 610;

float x = 0, y = 0, theta = 0;

long lastLeftTicks = 0;
long lastRightTicks = 0;

void setup() {
    Serial.begin(115200);
    motors.begin();
}

// ----- Compute odometry -----
void updateOdometry() {
    long L = SMotor2::tickCount; // left? if shared, you must maintain separate counts per motor
    long R = SMotor2::tickCount;

    long dL = L - lastLeftTicks;
    long dR = R - lastRightTicks;

    lastLeftTicks = L;
    lastRightTicks = R;

    float distPerTick = (2 * PI * WHEEL_RADIUS) / TICKS_PER_REV;
    float sL = dL * distPerTick;
    float sR = dR * distPerTick;

    float ds = (sL + sR) / 2.0;
    float dtheta = (sR - sL) / WHEEL_BASE;

    x += ds * cos(theta);
    y += ds * sin(theta);
    theta += dtheta;
}

// ----- Bézier curve -----
struct Point { float x, y; };

Point bezier(float t) {
    Point P0 = {0, 0};
    Point P1 = {0.914, 0};
    Point P2 = {1.828, 1.828};

    float u = 1 - t;

    return {
        u*u * P0.x + 2*u*t * P1.x + t*t * P2.x,
        u*u * P0.y + 2*u*t * P1.y + t*t * P2.y
    };
}

// ----- Pure pursuit -----
float lookahead = 0.20;   // meters
float baseSpeed = 0.12;   // m/s (tune to your robot)

void followPath() {
    for (float t = 0; t <= 1.0; t += 0.01) {

        updateOdometry();

        Point target = bezier(t);

        float dx = target.x - x;
        float dy = target.y - y;
        float dist = sqrt(dx*dx + dy*dy);

        if (dist < 0.01) continue;

        float pathAngle = atan2(dy, dx);
        float alpha = pathAngle - theta;

        float k = (2 * sin(alpha)) / lookahead;

        float vL = baseSpeed * (1 - k * WHEEL_BASE/2);
        float vR = baseSpeed * (1 + k * WHEEL_BASE/2);

        // Convert to steering and speed
        float steerNorm = (vR - vL) / baseSpeed; // -1..1
        int steerCmd = constrain(steerNorm * 100, -100, 100);

        int speedCmd = 50; // constant pace

        motors.run(steerCmd, speedCmd);
        

        delay(20);
    }

    motors.stop_motors();
}



void loop() {
    followPath();
    while(1);
}




// #include <SMotorPair.h>
// #include <ZebraGyro.h>
// #include <ZebraScreen.h>

// SMotorPair base(1,3);
// ZebraGyro gyro(7,39);
// ZebraScreen oled(0);

// void setup(){
//   Serial.begin(115200);
//   base.begin();
//   gyro.begin();
//  oled.begin();
//   oled.clear();
//   // base.move_rotations();
// }

// void loop(){
//  gyro.update();
//  int yaw = gyro.getYaw();
// //  oled.writeLine(1,String(yaw));
// // Serial.println(gyro.getYaw());
// base.run(yaw,50);

// }



// #include <Arduino.h>
// #include <ZebraScreen.h>

// // Screen is connected through I2C multiplexer at port 1
// ZebraScreen screen(0);

// void setup() {
//   Serial.begin(115200);
//   Serial.println("Initializing ZebraScreen...");

//   // Initialize the OLED
//   screen.begin();

//   // Show startup message
//   screen.write("Hello Zebra!");
//   delay(2000);

//   // Clear and prepare
//   screen.clear();
//   screen.writeLine(2, "ZebraScreen Test");
// }

// void loop() {
//   static int counter = 0;

//   // Update line 1 with counter value
//   screen.writeLine(3, "Counter: " + String(counter));

//   counter++;
//   delay(1000);
// }
