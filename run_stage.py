import os
import subprocess
import sys


def run(cmd):
    print("RUN:", cmd)
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print("FAILED:", cmd)
        sys.exit(1)


def has_device():
    result = subprocess.run("adb devices", shell=True, capture_output=True, text=True)
    print(result.stdout)
    return "\tdevice" in result.stdout


os.makedirs("assets/xml", exist_ok=True)

if not has_device():
    print("No emulator/device found. Start emulator first.")
    sys.exit(1)

run("adb shell screencap -p /sdcard/ui.png")
run("adb pull /sdcard/ui.png assets/ui.png")

run("adb shell uiautomator dump /sdcard/ui.xml")
run("adb pull /sdcard/ui.xml assets/xml/ui.xml")

run("python xml_parser.py")
run("python parser.py")

print("AUTO STAGE DONE")
