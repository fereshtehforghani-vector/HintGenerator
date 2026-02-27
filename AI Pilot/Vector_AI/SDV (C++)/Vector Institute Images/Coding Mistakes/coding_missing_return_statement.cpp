#include <Arduino.h>

int calculate() {
  int result = 5 + 5;
  // Missing return statement!
}
void setup() {
  int x = calculate();
}
void loop() {}
