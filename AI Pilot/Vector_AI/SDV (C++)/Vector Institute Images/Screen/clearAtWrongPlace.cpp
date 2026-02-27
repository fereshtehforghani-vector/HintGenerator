// Note: partial code shown — see full context in corresponding image
void loop() {
    static int counter = 0;

    // Update line 1 with counter value
    screen.writeLine(3, "Counter: " + String(counter));

    counter++;
    screen.clear();
    delay(1000);
}
