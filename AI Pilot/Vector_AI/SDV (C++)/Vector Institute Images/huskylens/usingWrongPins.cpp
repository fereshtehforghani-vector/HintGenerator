// Note: partial code shown — see full context in corresponding image
#include <Arduino.h>
#include "ZebraHuskyLens.h"

ZebraHuskyLens husky(15, 6);

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
