#ifndef ZebraTOF_h
#define ZebraTOF_h

#include <Arduino.h>
#include <Wire.h>
#include <VL53L0X.h>

class ZebraTOF {
  public:
    ZebraTOF(uint8_t port);
    void begin();
    // void begin(uint8_t address);  // For multiple sensors
    int readDistanceMean();
    int readDistance();
 

  private:
    uint8_t _port;
    uint8_t _address;
    VL53L0X _lox;
    void selectPort();
    void disablePort();
};

#endif