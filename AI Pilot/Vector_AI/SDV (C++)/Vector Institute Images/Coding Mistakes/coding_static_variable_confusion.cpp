#include <Arduino.h>

void printCount() {
  static int count = 0;
  count++;
  Serial.println(count);
}
void setup() {
  Serial.begin(115200);
  printCount();
  count = 0; 
}
void loop() {}
