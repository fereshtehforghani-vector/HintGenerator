---
module: 8
title: "Class 7: HuskyLens AI Camera"
course: "Self Driving Car"
course_code: "T600"
---

# Class 7: HuskyLens AI Camera
## Class 7: Introduction to HuskyLens

<!-- type: lesson -->

Class 7: Introduction to HuskyLens 

The **HuskyLens** is an easy-to-use **AI vision sensor** that allows robots to *see* and *understand* the world around them. Unlike regular sensors that only measure distance or color, HuskyLens uses a built-in camera and artificial intelligence to recognize **objects, faces, colors, lines, and tags**.

In our self-driving car project, the HuskyLens acts like the **eyes of the robot**, helping it make smarter decisions based on what it sees.

---


## **Why Use HuskyLens in a Self-Driving Car?**

Self-driving vehicles rely heavily on cameras to:


- 

Follow lanes


- 

Detect obstacles


- 

Recognize signs or markers


- 

Make navigation decisions



HuskyLens allows students to explore these real-world concepts **without needing advanced AI programming**. The AI models are trained directly on the device, making it perfect for learning and prototyping.

---


## **Key Features of HuskyLens**


- 

**Built-in AI processor** (no external AI computer needed)


- 

**Multiple AI modes**, including:


  - 

Object Tracking


  - 

Object Recognition


  - 

Color Recognition


  - 

Line Tracking


  - 

Tag (AprilTag-like) Recognition




- 

**Onboard screen** to preview what the camera sees


- 

**I2C and UART communication** for easy connection to microcontrollers


- 

Works well with **Arduino-based and custom controllers**



---


## **Communication with the Microcontroller**

In this course, the HuskyLens communicates with the robot controller using **I2C or Serial (UART)** communication.


- 

The camera processes the image internally


- 

It sends **processed results** (such as object position, ID, or size) to the microcontroller


- 

The microcontroller uses this data to control motors and steering



This approach keeps the code simple while still demonstrating powerful AI concepts.

---


## **Using Serial Monitor for Debugging**

To better understand how the camera works, we use **sample code** that prints HuskyLens data to the **Serial Monitor / Terminal**.

This allows students to:


- 

See real-time values such as:


  - 

Object ID


  - 

X and Y position


  - 

Width and height of detected objects




- 

Verify that the camera is detecting objects correctly


- 

Debug their logic before connecting the data to motors



Using the serial monitor helps bridge the gap between **what the robot sees** and **how the code reacts**.

---


## **Learning Outcomes**

By working with the HuskyLens camera, students will learn how to:


- 

Use vision sensors in robotics


- 

Understand how AI perception works in autonomous vehicles


- 

Read and interpret camera data using serial output


- 

Integrate camera-based decisions into robot movement


- 

Debug sensor data using the serial monitor

---

## Class 7: HuskyLens Attachment

<!-- type: lesson -->

Class 7: HuskyLens Attachment 

 

![image](https://dp4rp4tcpuoo1.cloudfront.net/SDV/image3.5.jpg)

![image](https://dp4rp4tcpuoo1.cloudfront.net/SDV/image3.4.jpg)

---

## Class 7: Programming with HuskyLens

<!-- type: lesson -->

Class 7: Programming with HuskyLens

Now that the HuskyLens camera is connected to the robot, the next step is learning how to read and use its data through code. While HuskyLens handles the complex image processing internally, it sends simple, easy-to-understand information to the microcontroller, such as object position, ID, size, or line location.

In this section, we will use a sample program to communicate with the HuskyLens and display the detected values on the Serial Monitor / Terminal. This helps us verify that the camera is working correctly and allows us to understand what the robot is “seeing” in real time.

Once you understand the output values from the camera, these same values can be used to control motors, steering, and decision-making in your self-driving car.
 

**Sample Code:**

![image](https://dp4rp4tcpuoo1.cloudfront.net/SDV/image3.6.png)

---

## Challenge #16: Lane Stripe Follower

<!-- type: challenge -->

Assignment: Challenge #16: Lane Stripe Follower

*Note: use STRIPE Competition Mat for this challenge.***

Your robot is now part of a smart delivery system that must stay within its assigned lane while driving through a city grid. The robot must see and follow the colored stripes on the road using the HuskyLens camera.

### **Objective**

Program the robot to follow a single colored stripe on the mat (yellow, blue, red, or purple) using the HuskyLens Line Tracking mode.

### **Challenge Rules**


- 

Select **Red stripe color** to follow.


- 

The robot must:


  - 

Stay centered on the stripe


  - 

Correct its steering using HuskyLens X-position data


  - 

Continue moving without touching other colored lines




- 

The robot should drive at least **one full straight segment** between two intersections.

