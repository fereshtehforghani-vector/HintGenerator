// Note: partial code shown — see full context in corresponding image
// ---------------------- LOOP ----------------------
void loop() {
    int start = millis(); // Record loop start time

    // Read distances (limit between 0-1200 mm)
    rightdist = constrain(right.readDistance1(), 0, 1200);
    leftdist  = constrain(left.readDistance1(), 0, 1200);
    frontdist = constrain(front.readDistance1(), 0, 1200);

    // Update gyro orientation
    gyro.update();
    yaw = gyro.getYaw();

    // Movement logic depending on number of turns
    if (count >= 1 && count < 12) {
    // If already turned at least once but less than 12 times
      if (side == 1) {
        rightdist = constrain(right.readDistance1(), 0, 1200);
        rforwardwall(yaw, rightdist); // Follow right wall
      } else {
        leftdist  = constrain(left.readDistance1(), 0, 1200);
        lforwardwall(yaw, leftdist); // Follow left wall
      }
