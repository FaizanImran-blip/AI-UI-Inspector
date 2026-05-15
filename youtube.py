import subprocess
import time


def adb(device_id, cmd):
    return subprocess.getoutput(f"adb -s {device_id} {cmd}")



def get_screen_size(device_id):
    output = subprocess.getoutput(f"adb -s {device_id} shell wm size")

    print("DEBUG wm size output:", output)  

    try:
        if ":" in output:
            size = output.split(":")[-1].strip()
        else:
            size = output.strip()

        if "x" not in size:

            print("⚠️ Invalid size detected, using fallback 1080x1920")
            return 1080, 1920

        width, height = size.split("x")
        return int(width), int(height)

    except Exception as e:
        print("⚠️ Screen size error:", e)
        return 1080, 1920


# ---------------- TAP ----------------
def tap_percent(device_id, x, y, w, h):
    adb(device_id, f"shell input tap {int(w*x)} {int(h*y)}")


# ---------------- TYPE ----------------
def type_text(device_id, text):
    adb(device_id, f"shell input text {text.replace(' ', '%s')}")


# ---------------- OPEN YOUTUBE ----------------
def open_youtube(device_id):
    print(f"🚀 Opening YouTube on {device_id}")

    adb(
        device_id,
        "shell monkey -p com.google.android.youtube -c android.intent.category.LAUNCHER 1",
    )

    time.sleep(6)


# ---------------- MAIN AUTOMATION ----------------
def youtube_automation(device_id):

    open_youtube(device_id)

    w, h = get_screen_size(device_id)
    time.sleep(3)

    # 🔍 search icon
    tap_percent(device_id, 0.90, 0.10, w, h)
    time.sleep(2)

    # search box
    tap_percent(device_id, 0.50, 0.20, w, h)
    time.sleep(1)

    # type query
    type_text(device_id, "MrBeast")
    adb(device_id, "shell input keyevent 66")

    time.sleep(5)

    # scroll loop
    while True:
        adb(device_id, "shell input swipe 500 1700 500 500 300")
        time.sleep(2)
