"""
checking...
"""

import subprocess

import sys
from python import start_device_pool
from python import task_queue


def run_command(cmd):
    """Run a shell command and return output."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
        return result.stdout.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", -1
    except Exception as e:
        return "", -1


def check_real_android_devices():
    print("\n[1] Checking Real Android Devices (ADB)...")
    output, code = run_command("adb devices")

    if code != 0:
        print("    ✗ ADB not found or not installed.")
        return []

    lines = output.splitlines()
    devices = []

    for line in lines[1:]:
        line = line.strip()

        if (
            "device" in line
            and "offline" not in line
            and "unauthorized" not in line
            and not line.startswith("emulator-")
        ):
            device_id = line.split()[0]

            name_output, _ = run_command(
                f"adb -s {device_id} shell getprop ro.product.model"
            )

            device_name = (
                name_output.strip() if name_output else "Unknown Android Device"
            )

            devices.append(
                {"id": device_id, "name": device_name, "type": "Real Android"}
            )

            print(f"    ✓ ACTIVE → {device_name} (ID: {device_id})")

    if not devices:
        print("    ✗ No real Android devices connected.")

    return devices


def check_android_emulators():
    """Check for running Android emulators."""
    print("\n[2] Checking Android Emulators...")
    output, code = run_command("adb devices")

    if code != 0:
        print("    ✗ ADB not found.")
        return []

    emulators = []
    lines = output.splitlines()

    for line in lines[1:]:
        line = line.strip()
        if line.startswith("emulator-"):
            emulator_id = line.split()[0]
            # Get AVD name
            avd_output, _ = run_command(f"adb -s {emulator_id} emu avd name")
            avd_name = (
                avd_output.splitlines()[0].strip() if avd_output else "Unknown AVD"
            )
            emulators.append(
                {"id": emulator_id, "name": avd_name, "type": "Android Emulator"}
            )
            print(f"    ✓ ACTIVE → {avd_name} (ID: {emulator_id})")

    # Also check available AVDs
    avd_output, _ = run_command("emulator -list-avds")
    if avd_output:
        print(
            f"    📋 Available AVDs (not necessarily running): {avd_output.replace(chr(10), ', ')}"
        )

    if not emulators:
        print("    ✗ No Android emulators currently running.")

    return emulators


def show_summary(all_devices):
    """Print final summary."""
    print("\n" + "=" * 55)
    print("           ACTIVE DEVICE SUMMARY")
    print("=" * 55)

    if not all_devices:
        print("  ✗ No active device found.")
        print("  → Connect a phone or boot a simulator/emulator.")
    else:
        for i, device in enumerate(all_devices, 1):
            print(f"  [{i}] {device['type']}")
            print(f"       Name : {device['name']}")
            print(f"       ID   : {device['id']}")
            print(f"       Status: ✓ ACTIVE")
            print()

    print("=" * 55)


def check_ios_simulators():
    print("\n[3] Checking iOS Simulators (Xcode)...")
    output, code = run_command("xcrun simctl list devices booted")

    if code != 0:
        print("    ✗ xcrun not found. Xcode may not be installed.")
        return []

    simulators = []
    lines = output.splitlines()

    for line in lines:
        line = line.strip()

        if "(Booted)" in line:
            clean_line = line.replace("(Booted)", "").strip()

            # safer parsing
            if "(" in clean_line and ")" in clean_line:
                name = clean_line.split("(")[0].strip()
                uuid = clean_line.split("(")[-1].replace(")", "").strip()
            else:
                name = clean_line
                uuid = "Unknown"

            simulators.append({"id": uuid, "name": name, "type": "iOS Simulator"})

            print(f"    ✓ ACTIVE → {name} (UUID: {uuid})")

    if not simulators:
        print("    ✗ No iOS simulator currently booted (Shutdown).")

    return simulators


def main():
    print("=" * 55)
    print("   DEVICE CHECKER - Mobile Automation Tool")
    print("   Checks: Real Phone | iOS Sim | Android Emu")
    print("=" * 55)

    all_active_devices = []

    # Check all three sources
    all_active_devices += check_real_android_devices()
    all_active_devices += check_android_emulators()
    all_active_devices += check_ios_simulators()

    # Final Summary
    show_summary(all_active_devices)
    start_device_pool(all_active_devices)
    while True:
        app = input("\nEnter app (chrome/docs/camera/exit): ")
        if app == "exit":
            print("👋 Exiting automation...")
            break
        print(f"📥 Received input: {app}")
        task_queue.put({"app": app})
        print("⏳ Task sent to device queue...\n")


if __name__ == "__main__":
    active_count = main()
    sys.exit(0 if active_count > 0 else 1)
