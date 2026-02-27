---
module: 7
title: "Class 6: Force/Touch Sensor"
course: "Reactive Robotics 2.0"
course_code: "R440"
---

# Class 6: Force/Touch Sensor
## Class 6: Force/Touch Sensor

<!-- type: lesson -->

Class 6: Force/Touch Sensor

![Taxi](https://dp4rp4tcpuoo1.cloudfront.net/R400V2/tsensor.png)

---

## Challenge #09: Mechanical - Attach Force Sensor

<!-- type: challenge -->

Assignment: Challenge #09: Mechanical - Attach Force Sensor



[Video: Programming Canvas](https://player.vimeo.com/video/1035653797)


**Rules:**


1. Attach a force sensor to your robot.

2. Be sure to use at least two friction pins—one might leave your robot wobbly, but two will lock it in place like a pro!

3. When you get done, show your coach before you submit your assignment. Remember to write done in the text box before you submit.

---

## Class 6: Wait Until Loop / Force Sensor

<!-- type: lesson -->

Class 6: Wait Until Loop / Force Sensor

The force sensor detects physical force in Newtons (a unit of measurement). It senses in three values:
1. Pressed - force detected above 0 Newtons
2. Hard-Pressed - force detected above 5 Newtons
3. Released - force detected  0 Newtons (no force)

Below are the blue sensor block options we have when using the force sensor. The pointed block is a conditional block that is waiting until the force sensor meet a condition. The rounded block is to read the values of the force sensor.
![code](https://dp4rp4tcpuoo1.cloudfront.net/R400V2/bluetouch.png)One of the most common ways to use the force sensor is with the **"Wait Until"** control block. Think of this block like a stop sign for your program—it pauses execution until a specific condition is met. However, unlike a real stop sign, any code that was already running will **keep going** until the condition is fulfilled. For example, if a **"Start Moving"** block is already active, the robot will continue moving until another **Motor Pair** block tells it to stop.

The "force sensor is pressed" is a conditional block that is waiting until the the condition of being pressed is "True" before it moves to the next line of code.

![code](https://dp4rp4tcpuoo1.cloudfront.net/R400V2/wup.png)
 

Below is an example of how we would use this as a full program. The robot starts and continues moving straight until the force sensor is pressed when it runs into the wall. 

![code](https://dp4rp4tcpuoo1.cloudfront.net/R400V2/wupf.png)

---

## Challenge #10: Force Sensor - Soccer Showdown

<!-- type: challenge -->

Assignment: Challenge #10: Force Sensor - Soccer Showdown

![map](https://dp4rp4tcpuoo1.cloudfront.net/R400V2/sbot.png)


![map](https://dp4rp4tcpuoo1.cloudfront.net/R400V2/sts.png)

**Rules:**
 


1. 
**Start your robot at Point B**, heading toward Point C.

2. 
**Use the force sensor** to detect the wall at the **yellow circle** and trigger a turn toward the stadium.

3. Continue driving toward the **soccer stadium**.

4. 
**Use the force sensor again** to detect the wall and bring the robot to a complete stop **right in front of the stadium**.


**Example Video:**
 

[Video: Programming Canvas](https://player.vimeo.com/video/1041868365)

---

## SOLUTIONS: Challenge #10: Force Sensor - Soccer Showdown

<!-- type: solution -->

SOLUTIONS: Challenge #10: Force Sensor - Soccer Showdown 

![code](https://dp4rp4tcpuoo1.cloudfront.net/R400V2/c4-soccercode.png)

---

## Class 6: Force Sensor as Trigger

<!-- type: lesson -->

Class 6: Force Sensor as Trigger

The Force Sensor acts like the robot’s go button—it detects when it’s pressed or touched, making it perfect for triggering a program to start. By integrating this sensor into your build, you can create an interactive and fun way to launch your robot's tasks. 

![code](https://dp4rp4tcpuoo1.cloudfront.net/R400V2/fstc.png)

---

## Challenge #11 - Force Sensor as Trigger - Wait Until - Fast Food Frenzy

<!-- type: challenge -->

Assignment: Challenge #11 - Force Sensor as Trigger - Wait Until - Fast Food Frenzy

![map](https://dp4rp4tcpuoo1.cloudfront.net/R400V2/ff.png)

---

## SOLUTION:  Challenge #11 - Force Sensor as Trigger - Wait Until - Fast Food Frenzy

<!-- type: solution -->

SOLUTION:  Challenge #11 - Force Sensor as Trigger - Wait Until - Fast Food Frenzy

Another way to do this code is to use a when started control block followed by a wait until force sensor is pressed blog. Both options solve this mission. 

![Code](https://dp4rp4tcpuoo1.cloudfront.net/R400V2/fff.png)

