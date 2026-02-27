#include <Arduino.h>

int a = 5, b = 10;
void setup() {}
void loop() {
  if(a > 0)
    if(b > 0)
      Serial.println("Both positive");
  else
    Serial.println("Huh?"); // Belongs to inner if!
}
