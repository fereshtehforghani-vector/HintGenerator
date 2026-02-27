// Note: partial code shown — see full context in corresponding image
void loop() {
    int distance = sensor.readDistance();


    if (distance < 300) {
        Serial.println("Going forward");
        motor.run_motor(60);
    }
    else {
        Serial.println("Stopping");
        motor.stop_motor();
    }

    delay(100);
}
