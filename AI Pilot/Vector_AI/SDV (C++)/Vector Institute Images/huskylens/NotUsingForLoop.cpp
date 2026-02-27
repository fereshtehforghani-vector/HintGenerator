// Note: partial code shown — see full context in corresponding image
    int i, id, x, y, w, h;
    i = 0;
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
    }


    Serial.println("========================================\n");

  } else {
    Serial.println("Failed to get data from HuskyLens");
  }

}
