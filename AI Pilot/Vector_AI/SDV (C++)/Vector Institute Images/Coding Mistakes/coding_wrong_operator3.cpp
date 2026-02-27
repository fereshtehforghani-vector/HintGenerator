#include <Arduino.h>
// MISTAKE 142
// Using single | instead of ||
bool flag1 = true, flag2 = false;
void setup() {}
void loop() {
  if(flag1 | flag2) {} // Should be ||
}
