import json
import cv2
import ui
import os


def medium_grouping(ui_boxes):
    medium_boxes = []

    for box in ui_boxes:
        x = box["x"]
        y = box["y"]
        w = box["width"]
        h = box["height"]
        area = w * h

        if 80 <= w <= 350 and 50 <= h <= 300 and 4000 <= area <= 80000:
            medium_boxes.append(
                {"type": "medium_ui_box", "x": x, "y": y, "width": w, "height": h}
            )

    return medium_boxes


def box_area(b):
    return b["width"] * b["height"]


def inside(parent, child, margin=8):
    return (
        child["x"] >= parent["x"] - margin
        and child["y"] >= parent["y"] - margin
        and child["x"] + child["width"] <= parent["x"] + parent["width"] + margin
        and child["y"] + child["height"] <= parent["y"] + parent["height"] + margin
    )


def soft_container_detection(image_path="assets/ui.png"):
    img = cv2.imread(image_path)
    img_h, img_w = img.shape[:2]
    screen_area = img_w * img_h

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # soft/light card boundaries ko enhance karo
    blur = cv2.GaussianBlur(gray, (7, 7), 0)

    # edges detect
    edges = cv2.Canny(blur, 20, 80)

    # gaps close karo taake rounded/card shape complete bane
    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT, (int(img_w * 0.04), int(img_h * 0.015))
    )

    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    boxes = []

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h

        if area < screen_area * 0.008:
            continue

        if area > screen_area * 0.45:
            continue

        if w < img_w * 0.18:
            continue

        if h < img_h * 0.035:
            continue

        boxes.append(
            {"type": "soft_container", "x": x, "y": y, "width": w, "height": h}
        )

    return boxes


def infer_parents_from_ocr(ocr_boxes, img_w, img_h):
    groups = []

    ocr_boxes = sorted(ocr_boxes, key=lambda b: b["y"])

    for box in ocr_boxes:
        added = False

        for group in groups:
            gy = sum(b["y"] for b in group) / len(group)

            if abs(box["y"] - gy) < img_h * 0.04:
                group.append(box)
                added = True
                break

        if not added:
            groups.append([box])

    parents = []

    for group in groups:
        if len(group) < 2:
            continue

        xs = [b["x"] for b in group]
        ys = [b["y"] for b in group]
        x2s = [b["x"] + b["width"] for b in group]
        y2s = [b["y"] + b["height"] for b in group]

        pad = int(img_w * 0.04)

        parents.append(
            {
                "type": "inferred_parent",
                "x": max(0, min(xs) - pad),
                "y": max(0, min(ys) - pad),
                "width": min(img_w, max(x2s) - min(xs) + pad * 2),
                "height": max(y2s) - min(ys) + pad * 2,
            }
        )

    return parents


def parent_grouping(
    image_path="assets/ui.png",
    final_boxes_path="assets/final_ui_boxes.json",
    ocr_boxes_path="assets/ocr_boxes_scaled.json",
    output_path="assets/parents.png",
):
    with open(final_boxes_path, "r") as f:
        ui_boxes = json.load(f)

    with open(ocr_boxes_path, "r") as f:
        ocr_boxes = json.load(f)

    img = cv2.imread(image_path)
    img_h, img_w = img.shape[:2]
    screen_area = img_w * img_h

    medium_boxes = medium_grouping(ui_boxes)
    soft_boxes = soft_container_detection(image_path)
    inferred_boxes = infer_parents_from_ocr(ocr_boxes, img_w, img_h)

    ui_boxes = ui_boxes + medium_boxes + soft_boxes + inferred_boxes

    margin = max(5, int(min(img_w, img_h) * 0.015))

    ui_boxes = attach_ocr_to_ui_boxes(
        ui_boxes,
        ocr_boxes,
        margin=margin
    )

    child_boxes = ui_boxes + ocr_boxes

    print("Inferred Parents:", len(inferred_boxes))
    print("Soft Containers:", len(soft_boxes))

    def is_noise(b):
        area = box_area(b)
        return area < screen_area * 0.00008

    ui_boxes = [b for b in ui_boxes if not is_noise(b)]
    child_boxes = [b for b in child_boxes if not is_noise(b)]

    def dynamic_margin():
        return max(5, int(min(img_w, img_h) * 0.015))

    margin = dynamic_margin()

    parents = []

    for parent in ui_boxes:
        parent_area = box_area(parent)
        if parent_area > screen_area * 0.65:
            continue

        # parent screen ka bohat chota part na ho
        if parent_area < screen_area * 0.01:
            continue

        children = []
        ui_count = 0
        ocr_count = len(parent.get("ocr_children", []))

        for child in child_boxes:
            if child == parent:
                continue

            child_area = box_area(child)

            # child parent se clearly chota hona chahiye
            if child_area >= parent_area * 0.70:
                continue

            if inside(parent, child, margin=margin):
                children.append(child)

                if child in ocr_boxes:
                    ocr_count += 1
                else:
                    ui_count += 1

        # parent score system
        score = 0

        # jitne zyada children, utna better parent
        score += min(len(children), 10) * 2

        # OCR text parent ke andar hai to strong signal
        score += min(ocr_count, 8) * 3

        # UI boxes bhi hain to signal
        score += min(ui_count, 8) * 2

        # bohat bara section/card parent ho sakta hai
        if parent_area >= screen_area * 0.04:
            score += 5

        # parent ka shape meaningful hona chahiye
        if parent["width"] > img_w * 0.25 and parent["height"] > img_h * 0.04:
            score += 4

        # minimum evidence
        if len(children) < 2:
            continue

        if score >= 12:
            parent_copy = parent.copy()
            parent_copy["children"] = children
            parent_copy["children_count"] = len(children)
            parent_copy["ocr_count"] = ocr_count
            parent_copy["ui_count"] = ui_count
            parent_copy["score"] = score
            if ocr_count >= 1 and len(children) >= 2 and score >= 10:
                parents.append(parent_copy)

    # high score parent first
    parents = sorted(parents, key=lambda p: p["score"], reverse=True)

    clean_parents = []
    print("PARENT CANDIDATES")
    for p in ui_boxes:
        print(
            p.get("type"), p["x"], p["y"], p["width"], p["height"], "area=", box_area(p)
        )

    for p in parents:
        keep = True

        for other in clean_parents:
            if inside(other, p, margin=margin):
                # agar p existing parent ke andar hai aur score low hai to skip
                if p["score"] <= other["score"]:
                    keep = False
                    break

            if inside(p, other, margin=margin):
                # agar p bara hai aur score better hai to chota parent hata do
                if p["score"] > other["score"]:
                    clean_parents.remove(other)

        if keep:
            clean_parents.append(p)

    for p in clean_parents:
        x, y, w, h = p["x"], p["y"], p["width"], p["height"]

        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 3)
        cv2.putText(
            img,
            f"Parent:{p['children_count']} S:{p['score']}",
            (x, max(20, y - 5)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            2,
        )

        for c in p["children"]:
            cx, cy, cw, ch = c["x"], c["y"], c["width"], c["height"]
            cv2.rectangle(img, (cx, cy), (cx + cw, cy + ch), (255, 0, 0), 1)

    os.makedirs("assets", exist_ok=True)

    cv2.imwrite(output_path, img)

    with open("assets/parent_groups.json", "w") as f:
        json.dump(clean_parents, f, indent=4)

    print("Parent grouping saved:", output_path)
    print("Parent JSON saved: assets/parent_groups.json")
    print("Total parents:", len(clean_parents))
    print("Original UI Boxes:", len(ui_boxes))
    print("Medium Boxes:", len(medium_boxes))
    print("Dynamic Margin:", margin)

    return clean_parents


def attach_ocr_to_ui_boxes(ui_boxes, ocr_boxes, margin=8):
    for ui in ui_boxes:
        ui["ocr_children"] = []

        for ocr in ocr_boxes:
            if inside(ui, ocr, margin=margin):
                ui["ocr_children"].append(ocr)

    return ui_boxes
