#include <Arduino.h>


int value = 5;
void setup() {
  float value = 3.14; 
  Serial.begin(115200);
}
void loop() {
  Serial.println(value); // Which one?
}
