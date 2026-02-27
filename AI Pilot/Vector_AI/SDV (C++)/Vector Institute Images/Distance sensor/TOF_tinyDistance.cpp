#include <Arduino.h>
#include <ZebraTOF.h>

ZebraTOF tof(2);
void setup() { 
  Serial.begin(115200);
  Wire.begin(); 
  tof.begin(); 

}
void loop() {
  int d = tof.readDistance();
  if(d < 10) {   // 10mm is tiny! Should be 100+
    Serial.println("STOP")
  } 
}
