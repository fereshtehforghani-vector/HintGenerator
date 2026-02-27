// Note: partial code shown — see full context in corresponding image
void loop() {
    static int counter = 0;
    screen.clear();
    // Update line 1 with counter value
    screen.writeLine(3, "This is a counter");
    screen.writeLine(3, "Counter: " + String(counter));
    counter++;
    delay(1000);
}
