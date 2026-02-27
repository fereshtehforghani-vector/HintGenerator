#include <Arduino.h>
#include <ZebraColour.h>

ZebraColour sensor(3);
ColourData data;
void setup() { Wire.begin(); sensor.begin(); }
void loop() {
  sensor.getFullColourData(data);
  if(data.colorID == 4) {} 
}
