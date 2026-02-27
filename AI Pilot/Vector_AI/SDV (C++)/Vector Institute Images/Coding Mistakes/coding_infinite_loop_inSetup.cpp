#include <Arduino.h>
// MISTAKE 61
// Infinite loop in setup
void setup() {
  while(true) {
    delay(100);
  }
  Serial.begin(115200); // Never reached!
}
void loop() {}
