#include <Arduino.h>
void setup(){
for(int i = 0; i < 10; i--) { // i decreases!
  Serial.println(i);
}
}
