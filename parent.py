import json
import cv2

import os


def medium_grouping(ui_boxes):
    medium_boxes = []

    for box in ui_boxes:
        x = box["x"]
        y = box["y"]
        w = box["width"]
        h = box["height"]
        area = w * h

        # small se bara, large se chota
        if 80 <= w <= 350 and 50 <= h <= 300 and 4000 <= area <= 80000:
            medium_boxes.append(
                {"type": "medium_ui_box", "x": x, "y": y, "width": w, "height": h}
            )

    return medium_boxes

def box_area(b):
    return b["width"] * b["height"]


def inside(parent, child, margin=8):
    return (
        child["x"] >= parent["x"] - margin and
        child["y"] >= parent["y"] - margin and
        child["x"] + child["width"] <= parent["x"] + parent["width"] + margin and
        child["y"] + child["height"] <= parent["y"] + parent["height"] + margin
    )


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
    medium_boxes = medium_grouping(ui_boxes)
    ui_boxes = ui_boxes + medium_boxes


    parent_candidates = [
        b for b in ui_boxes
        if b.get("type") in ["large_ui_box", "medium_ui_box"]
        and b["width"] >= 120
        and b["height"] >= 80
    ]

    child_boxes = ui_boxes + ocr_boxes
    parents = []

    for parent in parent_candidates:
        children = []

        for child in child_boxes:
            if child == parent:
                continue

            # child parent se chota hona lazmi hai
            if box_area(child) >= box_area(parent) * 0.75:
                continue

            if inside(parent, child, margin=10):
                children.append(child)

        # 1 child par parent mat banao, warna icon/button bhi parent ban jayega
        if len(children) >= 3:
            parent_copy = parent.copy()
            parent_copy["children"] = children
            parent_copy["children_count"] = len(children)
            parents.append(parent_copy)

    # duplicate/nested weak parents remove
    clean_parents = []

    for p in parents:
        duplicate = False

        for other in parents:
            if p == other:
                continue

            if inside(other, p, margin=5):
                # agar p chota hai aur other ke andar hai, to p ko skip karo
                if box_area(p) < box_area(other) * 0.85:
                    duplicate = True
                    break

        if not duplicate:
            clean_parents.append(p)

    img = cv2.imread(image_path)

    for p in clean_parents:
        x, y, w, h = p["x"], p["y"], p["width"], p["height"]

        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 3)
        cv2.putText(
            img,
            f"Parent: {p['children_count']}",
            (x, y - 5),
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

    return clean_parents