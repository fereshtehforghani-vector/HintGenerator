#include <Arduino.h>

void setup() {}
void loop() {
  for(int i = 0; i < 10; i++) {}
  Serial.println(i); // i not in scope!
}
