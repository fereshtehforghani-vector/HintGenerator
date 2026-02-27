// Note: partial code shown — see full context in corresponding image
    if (distance < 300) {
        Serial.println("Going forward");
        motor.stop_motor();
    }
    else {
        Serial.println("Stopping");
        motor.run_motor(60);
    }

    delay(100);
}
