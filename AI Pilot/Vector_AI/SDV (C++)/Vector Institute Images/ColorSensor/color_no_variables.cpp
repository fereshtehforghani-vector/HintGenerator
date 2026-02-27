#include <Arduino.h>
#include "ZebraColour.h"

ZebraColour sensor(3);
void setup() {
  Wire.begin();
  sensor.begin();
}
void loop() {
  ColourData data;
  sensor.getFullColourData(data); 
}
