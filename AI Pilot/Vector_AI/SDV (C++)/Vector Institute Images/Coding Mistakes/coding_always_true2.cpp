#include <Arduino.h>

void setup() {}
void loop() {
  if(5) { // Non-zero is true!
    Serial.println("Always");
  }
}
