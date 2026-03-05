#ifndef ZebraScreen_h
#define ZebraScreen_h

#include <Arduino.h>
#include <Wire.h>
#include <GyverOLED.h>

// ZebraScreen: Handles writing text to an SSH1106 OLED via I2C multiplexer
class ZebraScreen {
public:
  // Constructor: Accepts I2C multiplexer port
  ZebraScreen(uint8_t port);

  // Initializes the OLED screen
  void begin();

  // Writes a string to the screen
  void write(String msg);

  // Writes a string on a specific line
  void writeLine(uint8_t line, String msg);

  //Clears all writings on screen
  void clear();

private:
  void selectPort();  
  void disablePort();
  uint8_t _port;
  GyverOLED<SSH1106_128x64> oled;  
};

#endif
