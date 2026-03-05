
#include <Arduino.h>
#include "ZebraColour.h"

// Create color sensor on multiplexer port 0
ZebraColour colorSensor(1);

void setup() {
  Serial.begin(115200);
  Wire.begin();
  
  colorSensor.begin();
//   colorSensor.setLED(true); // Turn on LED
  
  delay(100);
}

void loop() {
  // METHOD 1: Get all data at once (FASTEST & RECOMMENDED)
  ColourData data;
  colorSensor.getFullColourData(data);
  
  Serial.println("\n=== Color Detection ===");
  Serial.printf("RGB: R=%d, G=%d, B=%d\n", data.r, data.g, data.b);
  Serial.printf("HSV: H=%.1f, S=%.2f, V=%.2f\n", data.h, data.s, data.v);
  Serial.printf("Lux: %.2f\n", data.lux);
  Serial.printf("Color: %s (ID: %d)\n", 
                colorSensor.getColourName(data.colorID), data.colorID);
  
  delay(500); // Read every 500ms (can go as fast as 50ms)
  
}

