// Note: partial code shown — see full context in corresponding image
void setup() {
    Serial.begin(115200);
    Wire.begin();

    sensor.begin();
    motor.begin();
    steering.begin();

    steering.run_angles(90);
    delay(2000);
}
