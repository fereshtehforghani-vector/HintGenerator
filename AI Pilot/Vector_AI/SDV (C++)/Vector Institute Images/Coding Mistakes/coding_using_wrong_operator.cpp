#include <Arduino.h>

int a = 5, b = 10;
void setup() {}
void loop() {
  if(a > 0 & b > 0) {} // Should be &&
}
