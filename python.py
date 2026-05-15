import queue
import threading
import time
from youtube import youtube_automation
import subprocess

device_states = {}


task_queue = queue.Queue()

APP_COMMANDS = {
    "chrome": ["com.android.chrome"],
    "docs": ["com.google.android.apps.docs"],
    "settings": ["com.android.settings"],
    "youtube": ["com.google.android.youtube"],
    "camera": [
        "com.google.android.GoogleCamera",
        "com.android.camera2",
        "com.sec.android.app.camera",
    ],
    "clock": ["com.google.android.deskclock", "com.sec.android.app.clockpackage"],
}


def open_app(device_id, app_key):
    packages = APP_COMMANDS.get(app_key, [])

    for package in packages:
        result = subprocess.getoutput(
            f"adb -s {device_id} shell monkey -p {package} -c android.intent.category.LAUNCHER 1"
        )

        if "Events injected" in result:
            print(f"🚀 Opened {app_key} using {package}")
            return  # STOP HERE

    # ONLY if ALL FAIL
    for package in packages:
        subprocess.run(
            f"adb -s {device_id} shell am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -p {package}",
            shell=True,
        )

    print(f"⚠️ Fallback used for {app_key}")


def start_device_pool(devices):
    for device in devices:
        threading.Thread(target=device_worker, args=(device,), daemon=True).start()


def device_worker(device):
    while True:
        task = task_queue.get()

        app_key = task.get("app")

        device_states[device["id"]] = "BUSY"

        if app_key == "youtube":
            youtube_automation(device["id"])
        else:
            open_app(device["id"], app_key)

        time.sleep(2)

        device_states[device["id"]] = "FREE"

        task_queue.task_done()
