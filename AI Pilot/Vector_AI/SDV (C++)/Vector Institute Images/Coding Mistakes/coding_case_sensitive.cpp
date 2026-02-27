#include <Arduino.h>

String input = "start";
void setup() {
  Serial.begin(115200);
}
void loop() {
  if(input == "START") {} // Case sensitive!
}
