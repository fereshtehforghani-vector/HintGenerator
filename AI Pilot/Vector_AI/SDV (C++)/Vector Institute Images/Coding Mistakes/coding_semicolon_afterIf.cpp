#include <Arduino.h>

int dist = 100;
void setup() {}
void loop() {
  if(dist < 50); // Extra semicolon!
    { /* This always runs! */ }
}
