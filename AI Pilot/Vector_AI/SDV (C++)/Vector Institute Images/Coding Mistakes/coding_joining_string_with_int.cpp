#include <Arduino.h>


int value = 42;
void setup() {
  Serial.begin(115200);
  Serial.println("Value: " + value); // Wrong!
}
void loop() {}
