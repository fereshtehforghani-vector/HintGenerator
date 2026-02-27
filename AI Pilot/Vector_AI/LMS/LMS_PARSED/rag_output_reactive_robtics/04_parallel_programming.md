---
module: 4
title: "Class 3: Parallel Programming"
course: "Reactive Robotics 2.0"
course_code: "R440"
---

# Class 3: Parallel Programming
## Class 3: Parallel Programming

<!-- type: lesson -->

Class 3: Parallel Programming

### **From Sequential to Parallel Programming**

Up until now, you’ve been using **sequential programming**—where your robot follows a **step-by-step** set of instructions, completing one action before moving on to the next. Think of it like checking off items on a to-do list: the robot finishes **one task at a time** before starting the next.

But in this lesson, we’re stepping up to **parallel programming**!

### **What is Parallel Programming?**

Parallel programming (aka broadcasting) lets your SPIKE Prime robot perform **multiple tasks at the same time**, just like how you can **walk and talk simultaneously**. Instead of waiting for one task to finish before starting another, your robot can handle multiple actions at once—making it **faster and more efficient**.

### **Example:**

🔹 Imagine your robot needs to **move forward** and **lift a claw**.
🔹 In **sequential programming**, the robot would move first, stop, and then lift the claw.
🔹 With **parallel programming (broadcasting)** the robot can move and lift the claw **at the same time**, completing the task more efficiently!

In SPIKE Prime, this happens when you use blocks like **"When Program Starts"** or **"When I receive broadcasting message"** to tell the robot to **work on two or more tasks at once**. It’s like assigning **each action its own worker**, so they all operate together!

Parallel programming is also known as **concurrent programming** or **multithreading**—all of which mean your robot is handling **multiple actions simultaneously**.

Now, let’s put this into practice and make your robot even smarter and faster

---

## Class 3:  Broadcasting / Parallel Programming Code

<!-- type: lesson -->

Class 3:  Broadcasting / Parallel Programming Code



![code](https://dp4rp4tcpuoo1.cloudfront.net/R400V2/bc1.png)

### **Making Your Robot Multitask: Display Colors & Count Simultaneously**

To make your robot display colors and count at the same time, we’ll turn this into a parallel program. Here’s how:


1. On the left side of the screen, click on the **"Events"** button.

2. Drag out a **"Broadcast Message"** block (green square in photo below) and create a new message. Name it **"Counting"**.


![code](https://dp4rp4tcpuoo1.cloudfront.net/R400V2/bc2b.png)

3. Grab a **"When I Receive"** block (blue square in photo above)and select **"Counting"** from the dropdown menu.

4. Attach your **counting code** to the **"When I Receive"** block.


![code](https://dp4rp4tcpuoo1.cloudfront.net/R400V2/bc3b.png)

---

## Class 3: Tips & Tricks - Wall Squaring

<!-- type: lesson -->

Class 3: Tips & Tricks - Wall Squaring



**Example of Wall Squaring Code:**

To wall square you simple run into a wall for seconds. 

![code](https://dp4rp4tcpuoo1.cloudfront.net/R400V2/wallsquarecode.png)

**Video Example of Wall Squaring:**

[Video: Programming Canvas](https://player.vimeo.com/video/1066429803)

 

**Reasons to Use Wall Squaring with a SPIKE Prime Robot:**


1. 


  1. 

**Fixes Drift** – The longer a robot drives, the more tiny errors add up, causing it to veer off course. Wall squaring resets its position for better accuracy.


  2. 

**Improves Mission Consistency** – By starting from a straight and known position, your robot is more likely to complete missions the same way every time.


  3. 

**Compensates for Wheel Slip** – If one wheel slips even a little, the robot's heading changes. Wall squaring realigns both wheels to keep movement predictable.


  4. 

**Makes Attachments More Reliable** – If your robot isn’t properly aligned, attachments might miss their targets. Squaring up ensures they connect as intended.


  5. 

**Saves Time and Effort** – Instead of fine-tuning every movement in code, wall squaring provides a simple physical correction that improves accuracy without extra programming.


  6. 

**Easy to Implement** – Just drive into a sturdy surface, stop both motors, and let the wall do the work. It’s a quick and effective way to reset alignment mid-run!

---

## Challenge #03: Parallel Programming & Forever Loop Block -  Street Sweeper Robot

<!-- type: challenge -->

Assignment: Challenge #03: Parallel Programming & Forever Loop Block -  Street Sweeper Robot

![truck](https://dp4rp4tcpuoo1.cloudfront.net/R400V2/SWTruck.png)

---

## SOLUTION: Challenge #03:  Parallel Programming & Forever Loop Block  - Street Sweeping Robot

<!-- type: solution -->

SOLUTION: Challenge #03:  Parallel Programming & Forever Loop Block  - Street Sweeping Robot

![code](https://dp4rp4tcpuoo1.cloudfront.net/R400V2/sweepercode.png)

---

## Challenge #04: Parallel Programming : Sparkle Town

<!-- type: challenge -->

Assignment:  Challenge #04: Parallel Programming : Sparkle Town

![map](https://dp4rp4tcpuoo1.cloudfront.net/R400V2/pwash2.png)

---

## SOLUTION Challenge #04:- Class 6 Parallel Programming : Sparkle Town

<!-- type: solution -->

SOLUTION Challenge #04:- Class 6 Parallel Programming : Sparkle Town

![code](https://dp4rp4tcpuoo1.cloudfront.net/R400V2/Sparkle1.png)
 

![code](https://dp4rp4tcpuoo1.cloudfront.net/R400V2/Sparkle2.png)

