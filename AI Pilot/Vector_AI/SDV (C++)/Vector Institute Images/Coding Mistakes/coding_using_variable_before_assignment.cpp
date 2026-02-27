#include <Arduino.h>

int speed;
void setup() {
  Serial.begin(115200);
  Serial.println(speed); // Undefined!
  speed = 50;
}
void loop() {}
