// Note: partial code shown — see full context in corresponding image
void loop() {
    int distance = sensor.readDistance();


    if (distance < 300) {
        Serial.println("Going forward");

    }
    else {
        Serial.println("Stopping");
        motor.run_motor(60);
    }

    delay(100);
}
