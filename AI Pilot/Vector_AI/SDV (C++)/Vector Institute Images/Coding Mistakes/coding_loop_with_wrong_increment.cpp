#include <Arduino.h>

void setup() {
  Serial.begin(115200);
}
void loop() {
  for(int i = 10; i > 0; i++) {} // Infinite loop!
}
