#include <Arduino.h>

void setup() {
  Serial.begin(115200);
  Serial.write("Hello"); // Should use println
}
void loop() {}
