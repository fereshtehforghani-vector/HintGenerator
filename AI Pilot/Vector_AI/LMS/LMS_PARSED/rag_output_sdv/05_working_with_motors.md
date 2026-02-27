---
module: 5
title: "Class 4: Working with Motors"
course: "Self Driving Car"
course_code: "T600"
---

# Class 4: Working with Motors
## Class 4: Introduction to DC Motors

<!-- type: lesson -->

Class 4: Introduction to DC Motors

[Video: Video](https://player.vimeo.com/video/1105554404)


A DC motor is a device that transforms electrical energy into motion. It operates on direct current (DC) electricity, converting the power into a rotating movement. When you supply it with electricity, it rotates and performs tasks like spinning a fan or propelling a robot. It's like using particular electricity to make things spin in circles!

![image ](https://dp4rp4tcpuoo1.cloudfront.net/SDC/image8.1.png)

**Where do we use them?**

Motors are like helpers that make things move when we use electricity. DC motors, in particular, are handy for various tasks. They're great for jobs like moving things on conveyor belts, spinning turntables, and other situations where we need to control speed and have steady, strong turning power. Imagine using a motor to make a toy train run at just the right speed or a factory conveyor belt move smoothly – DC motors are the go-to choice for these jobs!

**How do they work?**

The magic of electromagnetism powers DC motors. When electricity flows through a wire, it creates an invisible force called an electromagnetic field. This field makes the rotor (a part inside the motor) spin, and when it spins, it makes the motor's output shaft turn. It's like a secret force that turns the motor and makes machines move. So, DC motors use electricity and magnets to create motion!

![image ](https://dp4rp4tcpuoo1.cloudfront.net/SDC/image8.2.png)

A DC motor has two essential parts: the stator and the rotor. The stator doesn't move; it stays still. But it does something incredible—it creates a magnetic field. This magnetic field makes the rotor (the part that moves) spin around.

Here's how it works: Imagine a coil of wire with electricity flowing through it. This coil is wrapped around the motor's core. When the electricity flows, it creates an electromagnetic field right in the center of the coil. Then, the motor has some fixed magnets (the stator part). These magnets help focus the magnetic field created by the coil, making it spin. This spinning force is what makes the armature move and the motor work! It's like teamwork between magnets and electricity.

---

## Class 4: Programming Motors

<!-- type: lesson -->

Class 4: Programming Motors

### **Controlling Motors with SMotor and SMotorPair**

In your robot, motors can be programmed in two ways:


- 

**SMotor**: Use this when you want to control a **single motor**.


- 

**SMotorPair**: Use this when you're working with **two motors together**, such as when moving a drivetrain (like a car’s two wheels working together).



**Note: ***Since a self-driving car only uses one DC Motor and one Servo motor, we will only be using SMotor.*

### **Getting Started with SMotor**





To use a motor, follow these steps in your code:


1. 

Import the module at the top of your code:



*`#include<Wire.h>`*

*`#include<sMotor2.h>`*




2. 

Create your motor in the Constants section by specifying which port the motor is connected to:


*`SMotor2 motor2(2);`***




3. 

Start the motor pair in the `setup()` Function:


`*void setup() {
*`
  

`* Wire.begin();*`

    

`*motor2.begin();*`**


`*}*`



4. 

Control the motors in the `loop()` function using the `.move_time()` Function



![image](https://dp4rp4tcpuoo1.cloudfront.net/SDV/Image1.4.png)![image](https://dp4rp4tcpuoo1.cloudfront.net/SDV/image1.4.png)

`
`

---

## Challenge #06: Controlling DC Motor

<!-- type: challenge -->

Assignment: Challenge #06: Controlling DC Motor

Before jumping into the next challenge, let’s warm up with a few simple exercises to help you understand how to control a DC motor using code. These practice tasks will build your confidence and help you get comfortable with motor control basics.

### **Practice Exercises**

Use the `robot.move_time()` command to complete the following:


1. 

Make the robot move straight for **2 seconds**.


2. 

Make the robot move straight for **4 seconds**.


3. 

Make the robot move straight for **8 seconds**.



Each movement should be followed by a short pause using `delay(1000);` to help you observe each action.

---

## Class 4:  Introduction to Servo Motor

<!-- type: lesson -->

Class 4:  Introduction to Servo Motor

## **Introduction to Servo Motors**

Think of a **servo motor** as a highly precise motor — like a robotic arm that knows exactly where to go and stops at just the right spot. Imagine pointing a laser at a target and hitting it perfectly every time — that’s the level of accuracy we get with a servo motor!
 

### ![image ](https://dp4rp4tcpuoo1.cloudfront.net/SDC/image8.7.png)

### **Why Are Servo Motors So Accurate?**

What gives the servo motor its precision is a tiny internal "brain" called a feedback circuit. This circuit constantly monitors the motor’s position and speed. If something’s off, it immediately corrects it — just like a coach making sure every move is perfect.

We use servo motors in situations where high accuracy is required, such as:


- 

Rotating a robotic arm to grab an object


- 

Controlling steering in a remote-controlled car


- 

Operating camera gimbals, flight controls, and more



They’re basically the steady hands of the robotics world!

###  **How a Servo Motor Works**


Think of a servo motor as a team of three smart parts working together:


1. 

**Motor** – does the movement


2. 

**Output sensor (potentiometer)** – measures the actual position


3. 

**Feedback system (controller)** – compares the target position with the actual one and corrects it



This teamwork ensures every motion is accurate and well-controlled.
 

#### **Internal Components:**

**![image ](https://dp4rp4tcpuoo1.cloudfront.net/SDC/image8.8.png)**

As shown in the diagram below, a servo motor typically includes:


- 

A **DC motor**


- 

A **potentiometer**


- 

A **control circuit**


- 

A **gear assembly** to reduce speed and increase torque



Here's what happens step-by-step:


- 

You send a **target position** signal to the servo


- 

The **potentiometer** detects the current shaft position


- 

The controller compares the actual vs. desired position


- 

Any difference (error) is sent as a signal to correct the motor movement



This **closed-loop feedback system** ensures the output is precise.
 

**Sample Code to Control Servo:**

**![image](https://dp4rp4tcpuoo1.cloudfront.net/SDV/image1.5.png)**

---

## Challenge #07: Controlling Servo Motor

<!-- type: challenge -->

Assignment: Challenge #07: Controlling Servo Motor

### **Objective:**

Control a servo motor using PWM to move it between different angles.

### **Task:**

Write code that makes the servo motor move to the following angles in sequence:


- 

0°


- 

90°


- 

180°


- 

90°


- 

0°



Add a **1-second delay** between each movement so you can clearly see the servo turning.

### **What You’ll Learn:**


- 

How to send angle values to a servo motor


- 

How to control timing using `delay()`


- 

How servo motors respond to PWM signals

