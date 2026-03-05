# type: ignore
Import("env")  # noqa

# Add library paths and link flags
env.Append(
    LIBPATH=[
        "$PROJECT_DIR/lib/SMotor2/src",
        "$PROJECT_DIR/lib/ZebraServo/src",
        "$PROJECT_DIR/lib/SMotorPair/src",
        "$PROJECT_DIR/lib/ZebraGyro/src",
        "$PROJECT_DIR/lib/ZebraTOF/src"
    ],
    LIBS=[
        "SMotor2",
        "ZebraServo",
        "SMotorPair",
        "ZebraGyro",
        "ZebraTOF"
    ]
)

print("Added library paths:")
print("  - lib/SMotor2/src")
print("  - lib/ZebraServo/src")
print("  - lib/ZebraGyro/src")
print("  - lib/ZebraTOF/src")