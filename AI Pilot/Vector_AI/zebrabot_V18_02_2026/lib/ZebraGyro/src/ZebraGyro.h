#ifndef ZebraGyro_h
#define ZebraGyro_h

// Required libraries for MPU6050 and I2C communication
#include "Arduino.h"
#include "Wire.h"
#include "I2Cdev.h"
#include "MPU6050_6Axis_MotionApps20.h"

class ZebraGyro {
public:
  // Constructor: accepts optional I2C multiplexer port and interrupt pin
  ZebraGyro(uint8_t port = 0, uint8_t interruptPin = 39);

  // Initializes MPU6050
  void begin();

  // Reads and updates the latest yaw data from the MPU6050
  void update();

  // Returns current yaw angle in degrees (adjusted by resetYaw)
  float getYaw();

  // Resets yaw to zero (sets current yaw as the new reference)
  void resetYaw();

private:
  // Selects the proper port on the I2C multiplexer
  void selectPort();
  void disablePort();

  uint8_t _port;             // Port number on the I2C multiplexer (e.g., TCA9548A)
  uint8_t _interruptPin;     // Pin used for MPU interrupt

  bool _dmpReady;            // Flag: true if DMP initialized successfully
  uint8_t _mpuIntStatus;     // Holds MPU interrupt status
  uint8_t _devStatus;        // Result of DMP initialization (0 = success)
  uint16_t _packetSize;      // Expected size of DMP packet
  uint8_t _fifoBuffer[64];   // Buffer to hold data from FIFO

  float _lastYaw;            // Last recorded yaw value
  float _continuousYaw;      // Accumulated yaw over time (unwrapped)
  float _yawOffset;          // Offset applied to zero yaw (used in resetYaw)

  MPU6050 _mpu;              // MPU6050 device object
  Quaternion _q;             // Quaternion from DMP
  VectorFloat _gravity;      // Gravity vector calculated from DMP
  float _ypr[3];             // Yaw, pitch, roll array from DMP

  static volatile bool _mpuInterrupt; // Interrupt flag for MPU (shared across instances)

  // Interrupt Service Routine (ISR) triggered by MPU DMP interrupt
  static void dmpDataReady();
};

#endif
