#ifndef ZebraHuskyLens_h
#define ZebraHuskyLens_h

#include "Arduino.h"
#include "HUSKYLENS.h"

class ZebraHuskyLens {
  public:
    // Constructor
    ZebraHuskyLens(int rxPin = 4, int txPin = 0);
    
    // Initialize the HuskyLens
    bool begin();
    
    // Update data from HuskyLens (call this in loop)
    bool update();
    
    // Check if HuskyLens has learned anything
    bool isLearned();
    
    // Check if any object is detected
    bool isDetected();
    
    // Get number of detected objects
    int getObjectCount();
    
    // Get specific object data by index (0 to getObjectCount()-1)
    bool getObject(int index, int &id, int &xCenter, int &yCenter, int &width, int &height);
    
    // Get the first detected object
    bool getFirstObject(int &id, int &xCenter, int &yCenter, int &width, int &height);
    
    // Get object by ID (returns first match)
    bool getObjectByID(int targetID, int &xCenter, int &yCenter, int &width, int &height);
    
    // Get arrow data by index
    bool getArrow(int index, int &id, int &xOrigin, int &yOrigin, int &xTarget, int &yTarget);
    
    // Get X coordinate of first detected object
    int getX();
    
    // Get Y coordinate of first detected object
    int getY();
    
    // Get ID (color code) of first detected object
    int getID();
    
    // Get width of first detected object
    int getWidth();
    
    // Get height of first detected object
    int getHeight();
    
    // Print all detected objects to Serial
    void printAllObjects();
    
  private:
    HUSKYLENS _huskylens;
    HardwareSerial _mySerial;
    int _rxPin;
    int _txPin;
    int _objectCount;
    bool _dataValid;
};

#endif
