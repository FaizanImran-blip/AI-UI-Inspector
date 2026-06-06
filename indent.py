from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
from text_mapper import attach_text_to_ui_boxes
import ui
import os
import cv2
from parent import parent_grouping, medium_grouping
import json


def function_open_detection(path):
    os.makedirs("assets", exist_ok=True)
    img = cv2.imread(path)

    if img is None:
        print("ERROR: OpenCV image not loaded:", path)
        return []

    original = img.copy()
    debug_img = img.copy()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    thresh = cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 6
    )
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (35, 18))
    merged_img = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
    cv2.imwrite("assets/thresh.png", thresh)
    cv2.imwrite("assets/merged_img.png", merged_img)

    contours, hierarchy = cv2.findContours(
        merged_img, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE
    )

    boxes = []

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
        if not is_valid_ui_box(x, y, w, h, img):
            continue

        if w < 10 or h < 10:
            continue
        aspect = w / h

        if aspect > 8 or aspect < 0.10:
            continue
        if w > img.shape[1] * 0.90 and h > img.shape[0] * 0.90:
            continue
        img_h, img_w = img.shape[:2]

        if y > img_h * 0.88:
            box_type = "bottom_nav"
        elif area > 10000:
            box_type = "parent_box"
        else:
            box_type = "element_box"

        boxes.append(
            {
                "type": box_type,
                "x": int(x),
                "y": int(y),
                "width": int(w),
                "height": int(h),
            }
        )

    ocr_processed_path = improve_image_quality(path)
    ocr_boxes = function_ocr_boxes(ocr_processed_path)
    ocr_boxes = scale_ocr_boxes(ocr_boxes, scale=2)

    boxes = attach_text_to_ui_boxes(boxes, ocr_boxes)
    boxes = remove_duplicate_boxes(boxes)

    for i, b in enumerate(boxes):
        x, y, w, h = b["x"], b["y"], b["width"], b["height"]

        text = b.get("text", "")
        img_h, img_w = img.shape[:2]

        if "You" in text:
            b["type"] = "user_message"
        elif "Mentor AI" in text:
            b["type"] = "ai_message"
        elif y > img_h * 0.90:
            b["type"] = "input_bar"
        else:
            b["type"] = "ui_element"

        cv2.rectangle(original, (x, y), (x + w, y + h), (0, 255, 0), 2)

        cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(
            debug_img,
            str(i),
            (x, max(15, y - 5)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 255),
            1,
        )

    cv2.imwrite("assets/opencv_ui_detection.png", original)
    cv2.imwrite("assets/debug_numbered_boxes.png", debug_img)

    with open("assets/ui_boxes.json", "w", encoding="utf-8") as f:
        json.dump(boxes, f, indent=4)

    print("OpenCV UI detection saved: assets/opencv_ui_detection.png")
    print("Debug numbered boxes saved: assets/debug_numbered_boxes.png")
    print("UI boxes saved: assets/ui_boxes.json")
    print("Total boxes:", len(boxes))

    return boxes


def is_valid_ui_box(x, y, w, h, img):
    area = w * h
    img_h, img_w = img.shape[:2]

    if area < 1500:
        return False
    if w < 25 or h < 18:
        return False
    if w > img_w * 0.95 and h > img_h * 0.95:
        return False

    aspect = w / h
    if aspect > 8 or aspect < 0.15:
        return False

    return True


def remove_duplicate_boxes(boxes):
    final = []

    boxes = sorted(boxes, key=lambda b: b["width"] * b["height"], reverse=True)

    for box in boxes:
        keep = True

        for other in final:
            if is_inside(box, other):
                keep = False
                break

            if iou(box, other) > 0.75:
                keep = False
                break

        if keep:
            final.append(box)

    return final


def is_inside(a, b):
    ax1, ay1 = a["x"], a["y"]
    ax2, ay2 = a["x"] + a["width"], a["y"] + a["height"]

    bx1, by1 = b["x"], b["y"]
    bx2, by2 = b["x"] + b["width"], b["y"] + b["height"]

    return ax1 >= bx1 and ay1 >= by1 and ax2 <= bx2 and ay2 <= by2


def iou(a, b):
    ax1, ay1 = a["x"], a["y"]
    ax2, ay2 = a["x"] + a["width"], a["y"] + a["height"]

    bx1, by1 = b["x"], b["y"]
    bx2, by2 = b["x"] + b["width"], b["y"] + b["height"]

    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)

    inter_area = max(0, inter_x2 - inter_x1) * max(0, inter_y2 - inter_y1)

    area_a = a["width"] * a["height"]
    area_b = b["width"] * b["height"]

    union = area_a + area_b - inter_area

    if union == 0:
        return 0

    return inter_area / union


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
        if ui_box["type"] == "parent_box":
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

        if box["type"] == "parent_box":
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

    final_boxes = remove_duplicate_boxes(ui_boxes)

    draw_final_boxes(path, final_boxes)

    parent_grouping()
    ui.make_custom_ui_xml()
    return width, height


path = "assets/ui.png"
size = count_image_size(path)
