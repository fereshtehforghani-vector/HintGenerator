---
module: 4
title: "Class 3: Elements of Coding"
course: "Self Driving Car"
course_code: "T600"
---

# Class 3: Elements of Coding
## Class 3: Elements of Coding

<!-- type: lesson -->

Class 3: Elements of Coding

Coding is like giving instructions to a robot or computer so it knows exactly what to do. Every program — from a simple blinking light to a self-driving car — is built using a few core building blocks. Once you understand these building blocks, or elements, coding becomes much easier to read, write, and debug.

Coding can be thought of as two parts:


- 

**Algorithm** – the logic or step-by-step plan


- 

**Programming Language** – the grammar/syntax we use to write that logic



Let’s break coding down into six essential elements that form the foundation of every program:

### 1.  **Data**

Data is the information your program works with — like numbers, text, or sensor readings.

Example:




*int distance = 30;*


### **2. Variables**

Variables are containers that store data. You can change their values as your program runs.

Example:


*`int speed = 50;
`*

*`speed = 70; // update the value`*






### 3.  **Statements**

Statements are single lines of code that tell the program to do something — like a command or instruction.

Example:


*`digitalWrite(LED_BUILTIN, HIGH);`*


### 4.  **Operators**

Operators are symbols used to perform actions like math or comparisons.

Example:


`int total = 5 + 3;  // '+' is an arithmetic operator`


### 5.  **Conditions**

Conditions let your program make decisions. They verify the truth of something and then act accordingly.

Example:


*`if (distance < 20) `*

*`{
`*

*`  digitalWrite(LED_BUILTIN, HIGH);`*

*`}`*


### **6.  Loops**

Loops run code repeatedly until a condition is met — perfect for repeating actions.

Example:


*`for (int i = 0; i < 5; i++) `*

*`{
`*

*   `  digitalWrite(LED_BUILTIN, HIGH);
`*

*`  delay(500);
`*

*`  digitalWrite(LED_BUILTIN, LOW);
`*

*   `  delay(500);
`*

*`}`*


### **Summary**

Mastering these six elements will give you the tools to write your programs, troubleshoot problems, and build smarter, more complex projects. Think of them as your coding toolbox — the more comfortable you get with them, the more creative you can be!

---

## Class 3: Data and Variables

<!-- type: lesson -->

Class 3: Data and Variables

### **What is Data?**

**Data** is the foundation of all coding. Every line of code — even something as simple as:


*`Serial.println("Hello, world!");`*


Coding is essentially the process of manipulating data to control how computers or robots act and respond to input.

There are **three core data types**, and many others are combinations or extensions of these:

#### **1. Boolean**


- 

Simplest data type: only two possible values — `true` or `false`


- 

In electronics, it's often represented as `1` or `0` (HIGH or LOW)


- 

Commonly used in conditions and digital sensor readings




`*bool isObstacle = false;*`


#### **2. Numbers**


- 

Most frequently used data type in coding


- 

Subtypes include:


  - 

`int` – whole numbers (e.g. `*int count = 10;*`)


  - 

`float` – decimal numbers (e.g. `*float temp = 25.6;*`)


  - 

`long` / `double` – for more precision or larger ranges




- 

Critical for calculations, sensor values, timers, and more


 

#### **3. Characters & Strings**


- 

Characters (`char`) represent single letters or symbols


- 

Strings are collections of characters used for displaying text





*`char grade = 'A';
String message = "System Ready";`*

**Note:** Text-based data is less common in basic embedded electronics but important for displays and user interfaces.

 

### **Sensor Data Examples:**



| Sensor Type | Data Type | Example |
| --- | --- | --- |
| Digital Switch | Boolean | `HIGH` (1) or `LOW` (0) |
| Temperature Sensor | Number (`float`) | `23.4°C`, `float temp = analogRead(A0);` |
| LCD Display | Character/String | Showing `"Hello"` |




## **What is a Variable?**

A variable is a named container used to store data in a program. Think of it like a labelled box you can put data into and change whenever you need.

Each variable has:


- 

**A name** – what you call the box


- 

**A type** – the kind of data it stores (int, float, etc.)


- 

**A value** – the actual information stored



### **Example:**


![image ](https://dp4rp4tcpuoo1.cloudfront.net/SDC/Image3.3.PNG)



- 

`int` → variable type (integer)


- 

`pin` → variable name


- 

`13` → value assigned



You can now use this variable in your code like this:



*`pinMode(pin, OUTPUT);
digitalWrite(pin, HIGH);
`*



The benefit? If you ever want to change the pin number, you only update it once at the top of your code!




### **Why Are Variables Useful?**

Variables are especially powerful when dealing with values that change constantly, like sensor inputs or motor speeds.

For example, to control LED brightness using PWM:


*`int brightness = 128;
`*

*`analogWrite(ledPin, brightness);
`*


You can update the `brightness` variable over time to make the LED fade in and out.

### **In Summary:**


- 

**Data** is the information we use in our code — numbers, text, or true/false


- 

**Variables** are reusable, named containers that hold this data and make our programs dynamic, flexible, and readable



Mastering these concepts is key to writing smarter, more adaptable code!

---

## Class 3: OLED Display Integration

<!-- type: lesson -->

Class 3: OLED Display Integration

### **Introduction**

The SSH1106 OLED display is a small, lightweight screen that shows important information from your robot in real time. It’s perfect for projects where you want your robot to “talk back” to you by displaying data such as sensor readings, movement status, or debug messages. This makes your robot not only more interactive but also much easier to test and troubleshoot.

### **What is the SSH1106?**

The SSH1106 is a controller chip used in 128x64 pixel monochrome OLED displays. It's very similar to the more common SSD1306, but it has slight differences in how it handles memory addressing. The display communicates with your microcontroller over I2C, making it easy to wire and use with just two data pins.

### **What Can You Use It For?**


- 

Displaying distance values from the TOF sensor


- 

Showing angle data from the gyroscope


- 

Outputting current robot speed or direction


- 

Status updates (e.g., “Turning Left”, “Obstacle Detected”)


- 

Battery level or WiFi signal strength 



**Zebra Library **

The ZebraScreen library allows you to display text on an SSH1106 OLED screen connected via a TCA9548A I2C multiplexer. It's designed for simplicity—select the screen, write your message, and it handles the rest.

**Getting Started:**


1. **Add the library to your code **


*`   #include "ZebraScreen.h"`*
   

**2. Next, create a sensor object**

*`   ZebraGyro screen(0); // Will always be zero as that is the allocated spot for the Screen`*


- Can give it any name you want (replace the orange text with your choice).

- This should be in the global scope, before the setup() and loop() functions.

   

**3. Finally, initialize the motor.**
      

*`screen.begin();`*
 

**Sample Code:**

**![image](https://dp4rp4tcpuoo1.cloudfront.net/SDV/image2.5.png)**

**![image](https://dp4rp4tcpuoo1.cloudfront.net/SDV/image2.5b.png)**

---

## Challenge #03: Fade Master

<!-- type: challenge -->

Assignment: Challenge #03: Fade Master

### **Activity: Blink the Onboard LED on the Z-Bot Controller **

**Objective:**
In this activity, students will write and upload a simple code to blink an LED connected to GPIO pin 2 of the Z-Bot Controller (based on the ESP32 microcontroller). This serves as an introduction to embedded programming and digital output control.

---


### **Learning Outcomes**

By completing this activity, students will:


- 

Understand how to configure and use GPIO pins on the ESP32.


- 

Learn to write and upload basic code using VSCode.


- 

Observe how software can control hardware output (LED blinking).



---


###  **Instructions**



1. 

Connect the Z-Bot Controller to your computer using a USB cable.


2. 

Write the following code :


 


`![image](https://dp4rp4tcpuoo1.cloudfront.net/SDV/image2c.png)`

---

## Challenge #04: Ambulance Light

<!-- type: challenge -->

Assignment: Challenge #04: Ambulance Light

**Scenario:**
You’re the lead technician at a busy hospital. Just as the ambulance is about to head out for an emergency, its warning light fails! There’s no time to waste — you need to quickly build a replacement using the tools and components available.

Your task is to create a blinking, glowing ambulance light using an LED and code that mimics the real flashing effect — fading in and out at a specific speed.

### **Goal**

Write a program that makes an LED fade and glow like a flashing ambulance light using PWM (Pulse Width Modulation).

This sample code lets the LED fade in and out:

![image](https://dp4rp4tcpuoo1.cloudfront.net/SDV/Image1.2.PNG)

### **Concept Breakdown**

In the example code, you’ll see three key variables:


- 

**`led`** – This stores the GPIO PIN the LED is connected to.


- 

**`glow`** – This variable controls the brightness of the LED using a value between 0 (off) and 255 (fully on).


- 

**`fade`** – This controls the speed and direction of brightness changes. When `glow` reaches 0 or 255, `fade` reverses to make the LED fade in or out continuously.

---

## Class 3: Button Integration

<!-- type: lesson -->

Class 3: Button Integration 

**Introduction to Using Buttons**

Buttons are one of the simplest and most common inputs you can add to a project. They give users a direct way to send a signal to the microcontroller — for example, “Start now!” or “Change mode.”

**How a Button Works**
A button is essentially a small switch.


- 

When pressed, it **closes** the circuit, allowing current to flow.


- 

When released, it **opens** the circuit, stopping the current.



**Wiring the Button**

Most microcontrollers support a **`INPUT_PULLUP`** mode which uses an internal resistor to keep the input pin at a default HIGH state when the button isn’t pressed. This means:


- 

**Pressed button** → Pin reads **LOW** (connected to ground).


- 

**Released button** → Pin reads **HIGH** (pulled up by the resistor).



**Example Code**

Here’s a simple example showing how to set up and read a button:

![image](https://dp4rp4tcpuoo1.cloudfront.net/SDV/image1.3b.png)

---

## Challenge #05: Counter Command – Button Interface

<!-- type: challenge -->

Assignment: Challenge #05: Counter Command – Button Interface 

Welcome to **Z-Tech Robotics Lab**, where cutting-edge robots are developed to tackle real-world challenges. Today, your Z-Bot is being prepared for deployment in an automated warehouse, where it will assist in loading and unloading packages. But before it can be sent into the field, it needs a simple and intuitive **count tracking system**.

As a robotics engineer on the Z-Bot development team, your mission is to write the control logic for a **digital counter**. The Z-Bot has built-in push buttons and a screen—perfect tools to build a user interface for operators in the field.

Your task:


- 

Configure the **left button** to **decrease** the count (unloading items).


- 

Configure the **right button** to **increase** the count (loading items).


- 

Continuously show the current count on the **Z-Bot’s built-in display**.



This counter system will act as the Z-Bot’s visual interface for tracking items in real time. Your code is the brain behind this interaction.

---


### **Mission Objective:**


- 

Build a functional **increment/decrement counter system** using the built-in buttons on the Z-Bot.


- 

Display the counter value on the integrated screen.


- 

Ensure the system is responsive and user-friendly, just like a real-world embedded interface.



---


### **Guidelines:**


1. 

**Understand the Functionality:**
You’re creating a user interface where each button press affects a variable in memory, and that value is reflected on the screen.


2. 

**Plan the Logic:**


  - 

When the **right button** is pressed, the counter should go **up**.


  - 

When the **left button** is pressed, the counter should go **down**.


  - 

The display should always show the current count.




3. 

**Think About User Experience:**


  - 

What happens if the user presses too fast?


  - 

Should the counter stop at 0? Or go negative?


  - 

How will you avoid counting multiple times from one press?




4. 

**Test Your Implementation:**


  - 

Run your code on the Z-Bot.


  - 

Check that button presses affect the counter correctly.


  - 

Observe the screen for updates.

---

## Class 3: Statements, Operators, Conditions and Loops

<!-- type: lesson -->

Class 3: Statements, Operators, Conditions and Loops

Now that you understand data and variables, let’s explore how to use them to control your code and make your programs smart, interactive, and repetitive — just like real machines!

### **Statements**

Statements are the basic commands that tell your program what to do. Every line in your code that acts is a statement.

#### **Example:**


*`Serial.println("Hello");
`*


Here, *`Serial.println()`* is a statement that tells the program to print** “Hello” **on the terminal.


 You don’t need to memorize every command — just understand what each one does and when to use it.


### **Operators**

Operators are special symbols that let you perform arithmetic, comparisons, logical operations, and data manipulation. They’re the tools used to build smart logic in your program.

#### **Types of Operators:**



| **Type** | **Description** | **Examples** |
| --- | --- | --- |
| Arithmetic | Basic math | `+`, `-`, `*`, `/`, `%` |
| Comparison | Compare values | `==`, `!=`, `<`, `>`, `<=`, `>=` |
| Boolean (Logical) | Work with true/false | `&&` (AND), ` |
| Bitwise | Work on binary (0s & 1s) | `&`, ` |
| Compound Assignment | Shorthand math + assignment | `+=`, `-=`, `*=`, `/=`, `%=` |




#### **Example:**


*`int a = 10;
`*

*`int b = 5;
`*

*`int sum = a + b;      // Arithmetic
`*

*`if (a > b) { ... }    // Comparison`*


### **Conditions**

**C**onditional Statements allow your code to make decisions based on particular situations — like asking a yes/no question and doing something based on the answer.

Conditions make your program flexible and responsive.

####  Example:


*`if (temperature > 30)`*

*` {
`*

*     `  digitalWrite(fanPin, HIGH);
`*

*`}
`*


Here, the program checks if the temperature is higher than 30. If it is, it turns the fan ON.

### **Types of Conditional Statements**



| **Type** | **Description** |
| --- | --- |
| `if` | Runs code only if the condition is true |
| `if-else` | Chooses between two options |
| `if-else if-else` | Used when you have multiple conditions to check |




### **Loops**

Loops are used to repeat code automatically. Instead of writing the same thing over and over, loops do it for you — essential in automation and robotics.

####  **Example:**



*`for (int i = 0; i < 5; i++) `*

*`{
`*

*        ` digitalWrite(LED_BUILTIN, HIGH);
`*

*       `  delay(500);
`*

*       `  digitalWrite(LED_BUILTIN, LOW);
`*

*      `  delay(500);
`*

*`}`*


The above code blinks an LED 5 times using a `for` loop.
 

### **Types of Loops**



| Type | Description |
| --- | --- |
| `for` | Repeats a block of code a specific number of times |
| `while` | Repeats as long as a condition is true |
| `do-while` | Like `while`, but runs at least once |


### **In Summary**


- 

**Statements** tell the program what to do.


- 

**Operators** assist with tasks such as performing mathematical calculations or checking conditions.


- 

**Conditions** allow the program to make decisions.


- 

**Loops** repeat code, enabling automation.



These four elements bring your code to life — letting it **think, repeat, and adapt**.



.

