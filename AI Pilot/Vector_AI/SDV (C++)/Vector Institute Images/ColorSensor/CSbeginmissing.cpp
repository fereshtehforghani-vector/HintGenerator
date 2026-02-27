#include "ZebraColour.h"

// Create color sensor on port 1
ZebraColour colorSensor(1);

void setup() {
  Serial.begin(115200);
  Serial.println("Initializing color sensor...");
  Serial.println("Sensor ready!");
  delay(1000);
}

void loop() {
  // Get full color data
  ColourData colorData;
  colorSensor.getFullColourData(colorData);

  // Print detected color
  Serial.print("Detected Color: ");
  Serial.println(colorSensor.getColourName(colorData.colorID));

  // Print RGB values
  Serial.print("RGB: (");
  Serial.print(colorData.r);
  Serial.print(", ");
  Serial.print(colorData.g);
  Serial.print(", ");
  Serial.print(colorData.b);
  Serial.println(")");
}
