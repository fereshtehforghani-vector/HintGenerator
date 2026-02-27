#include <Arduino.h>
#include <ZebraTOF.h>

ZebraTOF tof(2);
int dist;
void setup() { 
  Wire.begin();
  Serial.begin(115200);
  tof.begin(); }
void loop() {
  
  if(dist < 100) { 
    Serial.println("stop");
   }
}
