#include <Arduino.h>

void setup() {}
void loop() {
  int count = 0; // Resets every loop!
  count++;
  Serial.println(count); // Always 1!
}
