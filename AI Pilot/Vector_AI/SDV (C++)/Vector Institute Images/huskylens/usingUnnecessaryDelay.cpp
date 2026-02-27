// Note: partial code shown — see full context in corresponding image
    // Loop through ALL detected objects
    for (int i = 0; i < totalObjects; i++) {
      int id, x, y, w, h;

      if (husky.getObject(i, id, x, y, w, h)) {
        Serial.print("Object #");
        Serial.print(i + 1);
        Serial.print(" - Color ID: ");
        Serial.print(id);
        Serial.print(", X: ");
        Serial.print(x);
        Serial.print(", Y: ");
        Serial.print(y);
        Serial.print(", Width: ");
        Serial.print(w);
        Serial.print(", Height: ");
        Serial.println(h);
        delay(1000);
      }
    }

    Serial.println("========================================\n");

  } else {
    Serial.println("Failed to get data from HuskyLens");
  }

  delay(2000); // Update every 500ms

}
