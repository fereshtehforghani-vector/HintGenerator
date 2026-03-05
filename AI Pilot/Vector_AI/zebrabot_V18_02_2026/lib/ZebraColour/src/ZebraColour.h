/*
 * ZebraColour.h
 * 
 * Library for TCS34725 RGB color sensor with TCA9548A I2C multiplexer
 * Supports full color detection and monochrome (white/black/gray) detection
 * 
 * Features:
 * - Fast 24ms integration time (~40 readings/second)
 * - HSV color space conversion
 * - 11 color detection + black/white/gray
 * - Monochrome mode with gray percentage (0% = black, 100% = white)
 * - "No Color" detection when nothing is in front of sensor
 */

#ifndef ZEBRACOLOUR_H
#define ZEBRACOLOUR_H

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_TCS34725.h>

// ============================================================================
// COLOR ID DEFINITIONS
// ============================================================================

#define COLOR_NONE    0   // Nothing detected (no object in front of sensor)
#define COLOR_BLACK   1
#define COLOR_WHITE   2
#define COLOR_GRAY    3
#define COLOR_RED     4
#define COLOR_ORANGE  5
#define COLOR_YELLOW  6
#define COLOR_GREEN   7
#define COLOR_CYAN    8
#define COLOR_BLUE    9
#define COLOR_PURPLE  10
#define COLOR_MAGENTA 11
#define COLOR_UNKNOWN 255

// ============================================================================
// DATA STRUCTURES
// ============================================================================

/**
 * Full color data structure
 * Contains raw RGB, HSV values, lux, and detected color ID
 */
struct ColourData {
  uint16_t r, g, b, c;  // Raw RGB + Clear channel values
  float h, s, v;        // HSV (Hue: 0-360°, Saturation: 0-1, Value: 0-1)
  float lux;            // Calculated luminosity
  uint8_t colorID;      // Detected color ID (use COLOR_* constants)
};

/**
 * Monochrome data structure
 * For white/black/gray detection with gray percentage
 */
struct MonochromeData {
  uint16_t r, g, b, c;  // Raw RGB + Clear channel values
  float h, s, v;        // HSV values
  float lux;            // Calculated luminosity
  uint8_t colorID;      // COLOR_NONE, COLOR_BLACK, COLOR_WHITE, COLOR_GRAY, or COLOR_UNKNOWN
  float grayPercentage; // 0% = black, 100% = white, -1 = not grayscale (colored object)
};

// ============================================================================
// ZEBRACOLOUR CLASS
// ============================================================================

class ZebraColour {
private:
  uint8_t _port;                  // Multiplexer port number
  Adafruit_TCS34725 *_tcs;        // Pointer to TCS34725 sensor object
  
  /**
   * Select the multiplexer port for this sensor
   * Called internally before sensor communication
   */
  void selectPort();
  void disablePort();

public:
  /**
   * Constructor
   * @param port - TCA9548A multiplexer port number (0-7)
   */
  ZebraColour(uint8_t port);
  
  /**
   * Initialize the color sensor
   * Must be called in setup() after Wire.begin()
   * Configures sensor with 24ms integration time and 4X gain
   */
  void begin();
  
  /**
   * Read raw color data from sensor
   * @param r - Red value (0-255)
   * @param g - Green value (0-255)
   * @param b - Blue value (0-255)
   * @param c - Clear channel value
   * @param lux - Calculated luminosity
   */
  void readColour(uint16_t &r, uint16_t &g, uint16_t &b, uint16_t &c, float &lux);
  
  /**
   * Convert RGB to HSV color space
   * @param r - Red value (0-255)
   * @param g - Green value (0-255)
   * @param b - Blue value (0-255)
   * @param h - Output hue (0-360 degrees)
   * @param s - Output saturation (0.0-1.0)
   * @param v - Output value/brightness (0.0-1.0)
   */
  void rgbToHSV(uint16_t r, uint16_t g, uint16_t b, float &h, float &s, float &v);
  
  // ========================================================================
  // FULL COLOR DETECTION (All Colors)
  // ========================================================================
  
  /**
   * Get color ID from HSV values (with debug output)
   * Detects all colors including black, white, gray, and "no color"
   * @param h - Hue (0-360)
   * @param s - Saturation (0.0-1.0)
   * @param v - Value/Brightness (0.0-1.0)
   * @return Color ID (use COLOR_* constants)
   */
  uint8_t getColourID(float h, float s, float v);
  
  /**
   * Get color name as string
   * @param colorID - Color ID (use COLOR_* constants)
   * @return Color name string (e.g., "Red", "Blue", "No Color")
   */
  const char* getColourName(uint8_t colorID);
  
  /**
   * Get complete color data in one call
   * Reads sensor, calculates HSV, and detects color
   * @param data - ColourData structure to fill
   */
  void getFullColourData(ColourData &data);
  
  // ========================================================================
  // MONOCHROME DETECTION (White/Black/Gray Only)
  // ========================================================================
  
  /**
   * Detect only monochrome colors (white/black/gray)
   * Returns COLOR_UNKNOWN for colored objects
   * @param h - Hue (0-360)
   * @param s - Saturation (0.0-1.0)
   * @param v - Value/Brightness (0.0-1.0)
   * @return COLOR_NONE, COLOR_BLACK, COLOR_WHITE, COLOR_GRAY, or COLOR_UNKNOWN
   */
  uint8_t detectMonochrome(float h, float s, float v);
  
  /**
   * Get grayscale percentage
   * @param v - Value/Brightness (0.0-1.0)
   * @param s - Saturation (0.0-1.0)
   * @return 0% = black, 100% = white, -1 = not a grayscale object
   */
  float getGrayPercentage(float v, float s);
  
  /**
   * Get complete monochrome data in one call
   * Reads sensor, detects monochrome color, and calculates gray percentage
   * Perfect for line-following robots
   * @param data - MonochromeData structure to fill
   */
  void getMonochromeData(MonochromeData &data);
};

#endif // ZEBRACOLOUR_H