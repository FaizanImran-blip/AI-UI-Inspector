from PIL import Image, ImageEnhance, ImageFilter
import pytesseract

import os
import cv2
from parent import parent_grouping, medium_grouping
import json


def function_open_detection(path):
    img = cv2.imread(path)

    if img is None:
        print("ERROR: OpenCV image not loaded")
        return []

    original = img.copy()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    """
    Large Boxes Detection
    Detecting big UI containers from screenshot
    """
    edges = cv2.Canny(gray, 40, 120)
    contours_large, _ = cv2.findContours(
        edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    ui_boxes = []

    for cnt in contours_large:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h

        if w > 30 and h > 20 and area > 800:
            ui_boxes.append(
                {"type": "large_ui_box", "x": x, "y": y, "width": w, "height": h}
            )
            cv2.rectangle(original, (x, y), (x + w, y + h), (0, 255, 0), 2)

    # ---------- SMALL COMPONENT DETECTION ----------
    blur = cv2.GaussianBlur(gray, (3, 3), 0)

    thresh = cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
    )

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    contours_small, _ = cv2.findContours(
        morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    for cnt in contours_small:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h

        if 6 <= w <= 80 and 6 <= h <= 80 and 30 <= area <= 3000:
            ui_boxes.append(
                {"type": "small_component", "x": x, "y": y, "width": w, "height": h}
            )
            cv2.rectangle(original, (x, y), (x + w, y + h), (255, 0, 0), 1)

    os.makedirs("assets", exist_ok=True)

    cv2.imwrite("assets/opencv_ui_detection.png", original)

    with open("assets/ui_boxes.json", "w", encoding="utf-8") as f:
        json.dump(ui_boxes, f, indent=4)

    print("OpenCV UI detection saved: assets/opencv_ui_detection.png")
    print("UI boxes saved: assets/ui_boxes.json")
    print("Total boxes:", len(ui_boxes))

    return ui_boxes


def function_ocr_boxes(path):
    img = Image.open(path)

    data = pytesseract.image_to_data(
        img, config="--oem 3 --psm 6", output_type=pytesseract.Output.DICT
    )

    boxes = []

    for i in range(len(data["text"])):
        text = data["text"][i].strip()

        if text == "":
            continue

        x = data["left"][i]
        y = data["top"][i]
        w = data["width"][i]
        h = data["height"][i]

        boxes.append({"text": text, "x": x, "y": y, "width": w, "height": h})

    with open("assets/ocr_boxes.json", "w", encoding="utf-8") as f:
        json.dump(boxes, f, indent=4)

    print("\nOCR boxes saved: assets/ocr_boxes.json")
    return boxes


def scale_ocr_boxes(boxes, scale=2):
    scaled = []

    for b in boxes:
        scaled.append(
            {
                "text": b["text"],
                "x": int(b["x"] / scale),
                "y": int(b["y"] / scale),
                "width": int(b["width"] / scale),
                "height": int(b["height"] / scale),
            }
        )

    return scaled


def overlap(a, b):
    ax1 = a["x"]
    ay1 = a["y"]
    ax2 = a["x"] + a["width"]
    ay2 = a["y"] + a["height"]

    bx1 = b["x"]
    by1 = b["y"]
    bx2 = b["x"] + b["width"]
    by2 = b["y"] + b["height"]

    return not (ax2 < bx1 or ax1 > bx2 or ay2 < by1 or ay1 > by2)


def remove_text_components(ui_boxes, ocr_boxes):
    clean_boxes = []

    for ui_box in ui_boxes:
        if ui_box["type"] == "large_ui_box":
            clean_boxes.append(ui_box)
            continue

        is_text = False

        for text_box in ocr_boxes:
            if overlap(ui_box, text_box):
                is_text = True
                break

        if not is_text:
            clean_boxes.append(ui_box)

    return clean_boxes


def improve_image_quality(input_path, output_path="assets/ui_processed.png"):
    if not os.path.exists(input_path):
        print("ERROR: file not found ->", input_path)
        return None

    img = Image.open(input_path).convert("L")

    w, h = img.size
    img = img.resize((w * 2, h * 2), Image.LANCZOS)

    img = ImageEnhance.Contrast(img).enhance(2.0)

    img = ImageEnhance.Sharpness(img).enhance(1.2)

    img = img.filter(ImageFilter.MedianFilter(size=3))

    img.save(output_path)

    print("OCR processed grayscale image saved:", output_path)
    return output_path


def function_ocr(path):
    img = Image.open(path)

    text = pytesseract.image_to_string(img, config="--oem 3 --psm 6")

    print("\nOCR Text:")
    print(text)

    return text


def draw_final_boxes(path, final_boxes, output_path="assets/final_detection.png"):
    img = cv2.imread(path)

    for box in final_boxes:
        x = box["x"]
        y = box["y"]
        w = box["width"]
        h = box["height"]

        if box["type"] == "large_ui_box":
            color = (0, 255, 0)
            thickness = 2

        elif box["type"] == "medium_ui_box":
            color = (0, 255, 255)
            thickness = 2

        else:
            color = (255, 0, 0)
            thickness = 1

        cv2.rectangle(img, (x, y), (x + w, y + h), color, thickness)

    cv2.imwrite(output_path, img)
    print("Final detection image saved:", output_path)

    with open("assets/final_ui_boxes.json", "w", encoding="utf-8") as f:
        json.dump(final_boxes, f, indent=4)

    print("Final clean UI boxes saved: assets/final_ui_boxes.json")
    print("Final boxes:", len(final_boxes))


def count_image_size(path):
    if not os.path.exists(path):
        print(f"ERROR: file not found -> {path}")
        return None

    img = Image.open(path)
    width, height = img.size

    print("PNG loaded successfully:", path)
    print("Width:", width)
    print("Height:", height)

    processed_path = improve_image_quality(path)

    # OCR text
    function_ocr(processed_path)

    # OCR boxes
    ocr_boxes = function_ocr_boxes(processed_path)

    # OCR image 2x resize hui thi, isliye boxes ko original size par lao
    ocr_boxes_scaled = scale_ocr_boxes(ocr_boxes, scale=2)

    with open("assets/ocr_boxes_scaled.json", "w", encoding="utf-8") as f:
        json.dump(ocr_boxes_scaled, f, indent=4)

    ui_boxes = function_open_detection(path)

    final_boxes = remove_text_components(ui_boxes, ocr_boxes_scaled)

    medium_boxes = medium_grouping(final_boxes)
    final_boxes.extend(medium_boxes)

    draw_final_boxes(path, final_boxes)

    parent_grouping()

    return width, height


path = "assets/ui.png"
size = count_image_size(path)
