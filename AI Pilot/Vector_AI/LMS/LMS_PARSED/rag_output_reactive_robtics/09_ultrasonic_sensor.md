---
module: 9
title: "Class 8: Ultrasonic Sensor"
course: "Reactive Robotics 2.0"
course_code: "R440"
---

# Class 8: Ultrasonic Sensor
## Class 8: Ultrasonic sensor

<!-- type: lesson -->

Class 8: Ultrasonic sensor

![robot](https://dp4rp4tcpuoo1.cloudfront.net/R400V2/ushouse.png)

The LEGO SPIKE Prime ultrasonic sensor is like giving your robot a pair of "bat ears" that let it “see” objects using sound waves. It works by emitting a high-pitched sound that’s way above what humans can hear. The sensor sends out this sound and then listens for the echo as it bounces back from an object. By measuring how long it takes for the sound to return, the sensor calculates the distance between the robot and whatever is in front of it. It’s like your robot shouting, "Hello?" and listening to hear how far away the reply comes from. This makes it perfect for navigating, avoiding obstacles, and detecting objects like a super-smart robot explorer!

---

## Challenge #14 - Attach Ultrasonic Sensor

<!-- type: challenge -->

Assignment:  Challenge #14 - Attach Ultrasonic Sensor



[Video: Programming Canvas](https://player.vimeo.com/video/1066427622)


**Rules:**


1. Attach an ultrasonic sensor to your robot.

2. Be sure to use at least two friction pins—one might leave your robot wobbly, but two will lock it in place like a pro!

3. When you get done, show your coach before you submit your assignment. Remember to write done in the text box before you submit.

---

## Class 8: Ultrasonic Sensor Code Blocks Part 1

<!-- type: lesson -->

Class 8: Ultrasonic Sensor Code Blocks Part 1

Here are the blue sensor block options available for the ultrasonic sensor. The pointed block functions as a conditional block, waiting until the ultrasonic sensor meets a specified condition. The rounded block is used to read the current values from the ultrasonic sensor.
![code](https://dp4rp4tcpuoo1.cloudfront.net/R400V2/usc2.png)
 

Here's an example of coding the ultrasonic sensor to wait until it detects an object within 2 inches of its range.

![code](https://dp4rp4tcpuoo1.cloudfront.net/R400V2/uscs.png)
 

Here's an example of how this would look as a complete program: The robot begins by moving forward and continues in a straight line until the ultrasonic sensor detects an object within 2 inches (5.08 centimeters). At that moment, the robot halts, activates the claw attachment connected to port C to drop it, and then reverses for 10 inches (25.4 centimeters).

![code](https://dp4rp4tcpuoo1.cloudfront.net/R400V2/uscl.png)

---

## Challenge #15: Ultrasonic Sensor to Trigger Turns- Morning Dough Dash

<!-- type: challenge -->

Assignment: Challenge #15: Ultrasonic Sensor to Trigger Turns- Morning Dough Dash

 

![map](https://dp4rp4tcpuoo1.cloudfront.net/R400V2/Flour.png)

---

## SOLUTION: Challenge #15: Ultrasonic Sensor to Trigger Turns- Morning Dough Dash

<!-- type: solution -->

SOLUTION: Challenge #15: Ultrasonic Sensor to Trigger Turns- Morning Dough Dash

![code](https://dp4rp4tcpuoo1.cloudfront.net/R400V2/c9-flour.png)

---

## Class 8: Ultrasonic Sensor Code Blocks Part 2

<!-- type: lesson -->

Class 8: Ultrasonic Sensor Code Blocks Part 2

![toolbox](https://dp4rp4tcpuoo1.cloudfront.net/R400V2/toolbox.png)


**
Ultrasonic Sensor Guard Dog Mode**
This code is like giving your robot a watchful guard mode! It uses the ultrasonic sensor to keep an eye (or ear) out for any movement in front of it. When something moves within its detection range, the robot springs into action and plays an alert sound—like it's shouting, “Hey, I see you!” This makes it perfect for a fun security system, a game of peek-a-boo, or any project where your robot needs to react to movement with a playful noise.

![code](https://dp4rp4tcpuoo1.cloudfront.net/R400V2/ustr.png)

**Ultrasonic Sensor Stop/Go on Detection**
This code is like giving your robot a magical “stop sign” sensor! The ultrasonic sensor acts as its lookout, scanning ahead as it moves. When the sensor detects an object up close, it sends a signal that tells the robot, “Whoa! Time to hit the brakes!” The robot then stops in its tracks, as if it just spotted a surprise roadblock. This makes it perfect for obstacle courses, avoiding crashes, or playing a game of robotic red light, green light!

![code](https://dp4rp4tcpuoo1.cloudfront.net/R400V2/usal.png)

**Ultrasonic Sensor Report What It Is Seeing**
This simple program is like having a live feed of what your robot is thinking and is an awesome troubleshooting tool when your code is acting up. If the numbers don’t make sense or your robot keeps seeing phantom objects, it might be time to relocate the ultrasonic sensor to a better viewing angle.

![code](https://dp4rp4tcpuoo1.cloudfront.net/R400V2/dw.png)

---

## Challenge #16: Ultrasonic Sensor - Guard Dog Mode - Art Heist

<!-- type: challenge -->

Assignment: Challenge #16: Ultrasonic Sensor - Guard Dog Mode - Art Heist

![map](https://dp4rp4tcpuoo1.cloudfront.net/R400V2/art.png)

---

## SOLUTION: Challenge #16: Ultrasonic Sensor - Guard Dog Mode - Art Heist

<!-- type: solution -->

SOLUTION: Challenge #16: Ultrasonic Sensor - Guard Dog Mode - Art Heist

![code](https://dp4rp4tcpuoo1.cloudfront.net/R400V2/artheist2.png)

---

## Challenge #17: Ultrasonic Sensor as a Trigger - City Hall Masterpiece

<!-- type: challenge -->

Assignment: Challenge #17: Ultrasonic Sensor as a Trigger - City Hall Masterpiece

![map](https://dp4rp4tcpuoo1.cloudfront.net/R400V2/art2.png)

---

## SOLUTION -Challenge #17: Ultrasonic Sensor as a Trigger - City Hall Masterpiece

<!-- type: solution -->

SOLUTION -Challenge #17: Ultrasonic Sensor as a Trigger - City Hall Masterpiece

![code](https://dp4rp4tcpuoo1.cloudfront.net/R400V2/artcity.png)

---

## Challenge #18: Ultrasonic Sensor Display Values - Robo-Ruler

<!-- type: challenge -->

Assignment: Challenge #18: Ultrasonic Sensor Display Values - Robo-Ruler

![map](https://dp4rp4tcpuoo1.cloudfront.net/R400V2/mtape.png)

---

## SOLUTION: Challenge #18: Ultrasonic Sensor Display Values - Robo-Ruler

<!-- type: solution -->

SOLUTION: Challenge #18: Ultrasonic Sensor Display Values - Robo-Ruler

![code](https://dp4rp4tcpuoo1.cloudfront.net/R400V2/roboruler.png)

