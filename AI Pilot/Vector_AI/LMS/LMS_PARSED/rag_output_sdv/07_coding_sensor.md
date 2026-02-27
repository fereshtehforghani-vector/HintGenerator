---
module: 7
title: "Class 6: Coding Sensor"
course: "Self Driving Car"
course_code: "T600"
---

# Class 6: Coding Sensor
## Class 6: Coding sensors - Time-of-Flight (TOF)

<!-- type: lesson -->

Class 6: Coding sensors - Time-of-Flight (TOF)

## TOF Sensor (VL53L0X)

The VL53L0X is a small and powerful Time-of-Flight (TOF) distance sensor. Unlike traditional infrared sensors that detect if something is near, this sensor can accurately measure how far an object is — using light!

![image](https://dp4rp4tcpuoo1.cloudfront.net/SDV/image1.8.png)

### **How Does It Work?**

The VL53L0X works like a super-fast stopwatch:


1. 

It sends out an invisible laser beam (don’t worry, it's safe and low-power).


2. 

The light bounces off an object in front of it.


3. 

The sensor measures how long it takes for the light to return.


4. 

Using that time, it calculates the exact distance to the object with accuracy down to the millimetre level.



This is why it’s called a Time-of-Flight sensor: it’s measuring the “flight time” of the light.

### **Why Is It Useful?**


- 

Precise distance measurement (up to ~2 meters)


- 

Works even in low light


- 

Better accuracy than ultrasonic or basic IR sensors


- 

Super small and easy to mount on a robot



**We often use it for:**


- 

Obstacle detection


- 

Wall-following robots


- 

Autonomous navigation


- 

Maintaining a safe distance


 

**ZebraTOF Library**

The **ZebraTOF **library is designed to work with VL53L0X Time-of-Flight (TOF) sensors using an I2C multiplexer. It makes it easy to:


-  Initialize sensors on specific ports

-  Read accurate distance measurements in millimetres

- Automatically switch I2C ports using a TCA9548A multiplexer

 

**Getting Started:**


1. **Add the library to your code **


*`   #include "ZebraTOF.h"`*

  2. **Next, create a sensor object**
      

*`ZebraTOF leftTOF(1) // Replace 1 with 1-6 depending on which port your sensor is connected to "ZebraTOF.h"`*


- Must use a sensor port (does not work with motor port).

- Can give it any name you want (replace orange text with name of your choice).

- This should be in the global scope, before the setup() and loop() functions.

 

   3. **Finally, initialize the motor**
      

*`leftTOF.begin()`*

Use the exact name you gave the sensor from the previous step.
 

**Example Code:**

**![image](https://dp4rp4tcpuoo1.cloudfront.net/SDV/image1.7.png)**

---

## Challenge #12: The Emergency Brake System

<!-- type: challenge -->

Assignment: Challenge #12: The Emergency Brake System

### **Scenario:**

Your robot car is cruising down the hospital hallway to deliver supplies. Suddenly, someone steps in front of it! Just like a real autonomous car, your robot must **detect obstacles in time and stop immediately** to avoid a collision.

### **Challenge Objective:**

Use the VL53L0X sensor to make your robot automatically stop when it detects an object in its path within a certain distance (e.g., 15 cm).

### **Requirements:**


- 

The robot should move forward normally.


- 

As soon as the TOF sensor detects an object closer than 15 cm, the robot must:


  - 

Stop immediately




- 

After the obstacle is removed, the robot can resume movement.



### **Bonus (Optional):**


- 

Make the robot slow down as it gets closer to the object, before stopping — like a genuine car braking smoothly.

---

## Challenge #13: Drive a Perfect Square

<!-- type: challenge -->

Assignment: Challenge #13: Drive a Perfect Square

### **Objective:**

Program your robot to drive in a square shape on the 8x8 ft table. At each corner, it should make a turn using the servo motor to change direction. The TOF sensor will help it detect if it’s getting too close to the wall and stop or adjust if needed.

### **Requirements:**


1. 


  1. 

Robot drives straight for a set distance (e.g., 6 feet).


  2. 

Uses servo steering to turn 90 degrees at each corner.


  3. 

Uses the TOF sensor to ensure it doesn’t crash into the wall:


    - 

If it senses an obstacle too close (less than 10 cm), the robot must stop or adjust before continuing.




  4. 

Completes a full square by repeating this 4 times.

---

## Class 6: Coding sensors - Gyro Sensor (MPU6050)

<!-- type: lesson -->

Class 6: Coding sensors - Gyro Sensor (MPU6050)

## **Gyro Sensor (MPU6050)**

The MPU6050 is a 6-axis motion sensor that combines:


- 

A 3-axis gyroscope – to measure rotation (how fast or how much the robot is turning),


- 

A 3-axis accelerometer – to measure acceleration and tilt (detects if the robot is going up/down or leaning).



This sensor is commonly used in mobile phones, drones, and robotics to detect motion, orientation, and balance.

### **What Does It Do for Your Robot?**

Using the MPU6050, your robot can:


- 

Measure how much it turns (yaw, pitch, roll),


- 

Detect sharp movements or tilts,


- 

Help the robot turn accurately by angle (e.g., turn 90°),


- 

Improve autonomous movement (e.g., making smooth or controlled curves).



### **How It Works in Our System**

In this class, we’re using our custom microcontroller and a custom MPU6050 library built specifically for our setup. This allows us to read directly:


- 

Raw gyro values (degrees per second),


- 

Angle estimation (via integration or filtering),


- 

Real-time motion data to make decisions.


 

**ZebraBot Library**

The ZebraGyro library is designed to work with MPU6050 gyroscopes using the DMP (Digital Motion Processor) for smooth and accurate yaw tracking. It supports using multiple gyros through a TCA9548A I2C multiplexer and can keep track of continuous rotation even beyond 360°


- Uses MPU6050’s DMP mode for precise orientation sensing.

- Keeps track of continuous yaw (even after 360 degrees).

 

**Getting Started:**


1. **Add the library to your code **


*`   #include "ZebraGyro.h"`*

   2. **Next, create a sensor object**

*`  ZebraGyro gyro(7); // Will always be 7 as that is the allocated spot for the Gyro Sensor on the board`*


- Can give it any name you want (replace orange text with name of your choice).

- This should be in the global scope, before the setup() and loop() functions.

 

    3. **Finally, initialize the motor**

*`    gyro.begin();`*
 

**Example Code:**

![image](https://dp4rp4tcpuoo1.cloudfront.net/SDV/image1.9.png)

---

## Challenge #14: Turns with Gyro

<!-- type: challenge -->

Assignment: Challenge #14: Turns with Gyro

### **Scenario:**

Your robot is navigating a square room and needs to make precise 90° turns at every corner to stay aligned with the walls. You’ve already attached the MPU6050 gyro sensor, and now it’s time to use it to control rotation accurately.

####  **Objective:**


Use the gyro sensor’s yaw data to make the robot:


- 

Move forward a set distance,


- 

Stop and rotate exactly 90° using gyro feedback,


- 

Repeat until the robot completes a perfect square path (4 turns).



#### **Challenge Steps:**


1. 

Initialize the MPU6050 and read yaw (Z-axis rotation) data.


2. 

Move forward in a straight line (use motor control).


3. 

Stop and begin rotating on the spot.


4. 

Monitor the yaw angle as the robot turns.


5. 

Stop rotating when the angle reaches ~90° (you may need to tune for overshoot).


6. 

Repeat this process four times to complete a square path.

---

## Class 6: I2C - RGB Color Sensor

<!-- type: lesson -->

Class 6: I2C - RGB Color Sensor

The TCS34725 is a powerful colour sensor that allows your robot to “see” colours — just like how your eyes can tell the difference between red, blue, green, and everything in between.

It works by detecting Red, Green, and Blue (RGB) values from a surface, which can then be used to identify different colours. This sensor also has a built-in infrared blocking filter and white LED, so it gives consistent readings even under varying light conditions.

![image](https://dp4rp4tcpuoo1.cloudfront.net/SDV/image2.0.jpg)

### **How It Works:**


- 

The sensor shines white light onto a surface using its built-in LED.


- 

It then measures the intensity of Red, Green, and Blue light reflected back from the surface.


- 

These values are combined to detect the actual colour.


- 

The sensor can also detect clear (ambient) light to adjust brightness sensitivity.



###  **Features:**



- 

I²C communication (easy to connect with most microcontrollers)


- 

Built-in white LED for accurate colour detection


- 

Detects a full range of colours


- 

Can differentiate between different shades of the same colour



### **Applications:**


- 

Line following using colour strips


- 

Colour-based sorting (e.g., red object vs. blue object)


- 

Detecting traffic lights in a simulated environment


- 

Triggering different behaviours based on detected colours (e.g., slow down at red)


 

**ZebraBot Libaray: **

The ZebraColour library is designed to work with TCS34725 RGB colour sensors via an I2C multiplexer. It helps you:


- 
Initialize colour sensors on specific ports



- 
Read RGB, clear light, and lux data.



- 
Automatically switch I2C ports using a TCA9548A multiplexer.



- Identify basic colours (Yellow, Red, Blue, Green, Black)


**Getting Started:**


1. Add the library to your code 


*`   #include "ZebraColour.h"`*

   2. Next, create a sensor object

*`   ZebraColour colourSensor(1);`* // Replace 1 with 1-6 depending on which port your sensor is connected to.


- 


  - Must use a sensor port (does not work with motor port).

  - Can give it any name you want (replace orange text with name of your choice).

  - This should be in the global scope, before the setup() and loop() functions.




     3. Finally, initialize the Sensor.
        

*`colourSensor.begin()`*

**Example Code:****

*`![image](https://dp4rp4tcpuoo1.cloudfront.net/SDV/image2.11.png)`*

---

## Challenge #15: Color Path Navigator

<!-- type: challenge -->

Assignment: Challenge #15: Color Path Navigator

### **Scenario:**

You are part of a rescue robot team. Your robot needs to follow a colour-coded path on the floor to reach a target destination. The floor is marked with colour checkpoints that give the robot instructions. Your job is to program the robot to recognize different colours and perform specific actions based on what it sees.

### **Task:**

Using the TCS34725 RGB Colour Sensor mounted on your robot and the code you’ve learned so far, **make your **robot detect and respond to different colours placed on the track.

### **Goals:**


- 

**Green**: Move forward


- 

**Blue**: Turn right


- 

**Yellow**: Turn left


- 

**Red**: Stop for 3 seconds 


- 

**Black**: End of track — stop the robot

