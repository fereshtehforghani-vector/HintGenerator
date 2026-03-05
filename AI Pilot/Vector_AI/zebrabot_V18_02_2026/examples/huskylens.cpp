
#include <Arduino.h>
#include "ZebraHuskyLens.h"

ZebraHuskyLens husky(4, 0);

void setup() {
  if (!husky.begin()) {
    Serial.println("Failed to initialize HuskyLens!");
    while(1);
  }
  Serial.println("HuskyLens Ready - Detecting All Objects");
}

void loop() {
  if (husky.update()) {
    
    if (!husky.isLearned()) {
      Serial.println("Nothing learned yet!");
      delay(1000);
      return;
    }
    
    if (!husky.isDetected()) {
      Serial.println("No objects detected");
      delay(500);
      return;
    }
    
    // Get total count of objects detected
    int totalObjects = husky.getObjectCount();
    Serial.println("\n========================================");
    Serial.print("Total Objects Detected: ");
    Serial.println(totalObjects);
    Serial.println("========================================");
    
    // Loop through ALL detected objects
    for (int i = 0; i < totalObjects; i++) {
      int id, x, y, w, h;
      
      if (husky.getObject(i, id, x, y, w, h)) {
        Serial.print("Object #");
        Serial.print(i + 1);
        Serial.print(" - Color ID: ");
        Serial.print(id);
        Serial.print(", X: ");
        Serial.print(x);
        Serial.print(", Y: ");
        Serial.print(y);
        Serial.print(", Width: ");
        Serial.print(w);
        Serial.print(", Height: ");
        Serial.println(h);
      }
    }
    
    Serial.println("========================================\n");
    
  } else {
    Serial.println("Failed to get data from HuskyLens");
  }
  
  delay(500); // Update every 500ms
}