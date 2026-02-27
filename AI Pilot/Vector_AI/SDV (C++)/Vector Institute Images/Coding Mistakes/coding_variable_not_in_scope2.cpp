#include <Arduino.h>

void setup() {
  if(true) {
    int temp = 25;
  }
  Serial.begin(115200);
  Serial.println(temp); // Not in scope!
}
void loop() {}
